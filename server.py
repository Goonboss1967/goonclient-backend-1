#!/usr/bin/env python3
"""
GoonClient Cosmetics-Backend (nur Python-Standardbibliothek, Python 3.9+).

Speichert pro Spieler-UUID, welche Cape, welches Badge und welches animierte Namensschild er ausgerüstet hat,
und liefert das an andere GoonClient-Spieler aus. Damit sehen sich GoonClient-Nutzer gegenseitig auf JEDEM Server,
auch auf Servern ohne GoonClient (z.B. DuelPrac.net).

Sicherheit: Wer Daten ändern will, muss beweisen, dass ihm die UUID gehört. Das geht über den normalen
Minecraft-Login (Mojang Session-Server): Der Client meldet sich mit einer vom Server vorgegebenen "serverId" bei
Mojang an ("join"), danach fragt dieser Server bei Mojang nach ("hasJoined"). Das Minecraft-Zugangstoken verlässt
dabei nie den Computer des Spielers und geht nie an diesen Server.

Starten:   python3 server.py --host 0.0.0.0 --port 8080 --db goonclient.db
Testen:    python3 server.py --insecure   (KEIN Mojang-Login, nur für lokale Tests!)
Für das Internet unbedingt hinter HTTPS betreiben (z.B. nginx/Caddy als Reverse-Proxy, dann --trust-proxy).

Schnittstelle (alles JSON):
  GET  /v1/health
  POST /v1/auth/challenge                      -> {"serverId": "..."}
  POST /v1/auth/verify   {"username","serverId"} -> {"token","uuid","expiresIn"}
  PUT  /v1/cosmetics     (Authorization: Bearer <token>) Body: Cosmetics-Objekt
  GET  /v1/cosmetics?uuids=<uuid>,<uuid>,...   (höchstens 100) -> {"players": {"<uuid>": Cosmetics-Objekt}}
"""
import argparse
import json
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid as uuidlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ID_RE = re.compile(r"^[a-z0-9_]{0,24}$")
MAX_BODY = 2048
MAX_UUIDS = 100
CHALLENGE_TTL = 60
TOKEN_TTL = 3600
RECORD_MAX_AGE = 60 * 24 * 3600  # 60 Tage ohne Lebenszeichen: Eintrag wird gelöscht

DEFAULTS = {
    "cape": "", "badge": "", "badgeColor": 0xFFFFFF, "badgeText": "", "badgePrefix": False,
    "tag": "", "tagColor1": 0xFFFFFF, "tagColor2": 0xFFFFFF, "tagSpeed": 0, "tagBold": False,
}


def clean_text(text, limit=8):
    """Wie CosmeticsRules.cleanBadgeText im Client: keine Steuerzeichen, kein Paragraphzeichen, höchstens `limit` Zeichen."""
    if not isinstance(text, str):
        return ""
    out = []
    for ch in text:
        cp = ord(ch)
        if cp < 32 or cp == 127 or cp == 0xA7 or 0x80 <= cp < 0xA0:
            continue
        out.append(ch)
        if len(out) >= limit:
            break
    return "".join(out).strip()


def as_int(value, lo, hi, default):
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(lo, min(hi, value))


def as_id(value):
    return value if isinstance(value, str) and ID_RE.match(value) else ""


def clean_cosmetics(raw):
    """Prüft einen Cosmetics-Eintrag. Unbekannte Felder werden verworfen, ungültige Werte durch Standardwerte ersetzt."""
    if not isinstance(raw, dict):
        raise ValueError("body must be a JSON object")
    return {
        "cape": as_id(raw.get("cape")),
        "badge": as_id(raw.get("badge")),
        "badgeColor": as_int(raw.get("badgeColor"), 0, 0xFFFFFF, 0xFFFFFF),
        "badgeText": clean_text(raw.get("badgeText")),
        "badgePrefix": raw.get("badgePrefix") is True,
        "tag": as_id(raw.get("tag")),
        "tagColor1": as_int(raw.get("tagColor1"), 0, 0xFFFFFF, 0xFFFFFF),
        "tagColor2": as_int(raw.get("tagColor2"), 0, 0xFFFFFF, 0xFFFFFF),
        "tagSpeed": as_int(raw.get("tagSpeed"), 0, 400, 0),
        "tagBold": raw.get("tagBold") is True,
    }


def norm_uuid(text):
    return str(uuidlib.UUID(text))


class Store:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS cosmetics (uuid TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)")
        self.db.commit()
        self.purge()

    def purge(self):
        with self.lock:
            self.db.execute("DELETE FROM cosmetics WHERE updated < ?", (time.time() - RECORD_MAX_AGE,))
            self.db.commit()

    def put(self, uid, data):
        with self.lock:
            self.db.execute("INSERT INTO cosmetics(uuid, data, updated) VALUES(?,?,?) "
                            "ON CONFLICT(uuid) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                            (uid, json.dumps(data), time.time()))
            self.db.commit()

    def get_many(self, uids):
        result = {}
        with self.lock:
            for uid in uids:
                row = self.db.execute("SELECT data FROM cosmetics WHERE uuid=?", (uid,)).fetchone()
                if row:
                    result[uid] = json.loads(row[0])
        return result


class RateLimiter:
    """Einfaches Fenster pro IP und Gruppe, schützt vor Dauerfeuer."""

    def __init__(self):
        self.lock = threading.Lock()
        self.hits = {}

    def allow(self, ip, group, limit, window=60.0):
        now = time.time()
        with self.lock:
            key = (ip, group)
            arr = [t for t in self.hits.get(key, []) if now - t < window]
            if len(arr) >= limit:
                self.hits[key] = arr
                return False
            arr.append(now)
            self.hits[key] = arr
            if len(self.hits) > 20000:  # Speicher begrenzen
                self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < window}
            return True


class State:
    def __init__(self, args):
        self.args = args
        self.store = Store(args.db)
        self.limiter = RateLimiter()
        self.lock = threading.Lock()
        self.challenges = {}   # serverId -> Ablaufzeit
        self.tokens = {}       # token -> (uuid, Ablaufzeit)

    def new_challenge(self):
        sid = secrets.token_hex(20)
        with self.lock:
            now = time.time()
            self.challenges = {k: v for k, v in self.challenges.items() if v > now}
            if len(self.challenges) > 5000:
                raise RuntimeError("too many pending challenges")
            self.challenges[sid] = now + CHALLENGE_TTL
        return sid

    def take_challenge(self, sid):
        with self.lock:
            exp = self.challenges.pop(sid, None)
        return exp is not None and exp > time.time()

    def issue_token(self, uid):
        token = secrets.token_urlsafe(24)
        with self.lock:
            now = time.time()
            self.tokens = {k: v for k, v in self.tokens.items() if v[1] > now}
            self.tokens[token] = (uid, now + TOKEN_TTL)
        return token

    def uuid_for(self, token):
        with self.lock:
            entry = self.tokens.get(token)
        if entry and entry[1] > time.time():
            return entry[0]
        return None


def mojang_has_joined(state, username, server_id):
    """Fragt bei Mojang, ob `username` sich mit dieser serverId angemeldet hat. Gibt die UUID zurück oder None."""
    url = state.args.mojang.rstrip("/") + "/session/minecraft/hasJoined?" + urllib.parse.urlencode(
        {"username": username, "serverId": server_id})
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            if resp.status != 200:
                return None
            body = json.loads(resp.read(4096).decode("utf-8"))
            return norm_uuid(body["id"])
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
        return None


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GoonClientBackend/1.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            if state.args.verbose:
                super().log_message(fmt, *args)

        def client_ip(self):
            if state.args.trust_proxy:
                fwd = self.headers.get("X-Forwarded-For", "")
                if fwd:
                    return fwd.split(",")[0].strip()
            return self.client_address[0]

        def send_json(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if code >= 400:
                # Bei Fehlern wurde der Body evtl. nicht gelesen: Verbindung schließen, damit nichts durcheinander kommt
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            self.wfile.write(body)

        def error(self, code, message):
            self.send_json(code, {"error": message})

        def read_json(self):
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length < 0 or length > MAX_BODY:
                raise ValueError("body too large")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def bearer(self):
            auth = self.headers.get("Authorization", "")
            return auth[7:].strip() if auth.startswith("Bearer ") else ""

        def guard(self, group, limit):
            if not state.limiter.allow(self.client_ip(), group, limit):
                self.error(429, "too many requests")
                return False
            return True

        # ---------- Routen ----------

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            try:
                if parsed.path == "/v1/health":
                    return self.send_json(200, {"ok": True})
                if parsed.path == "/v1/cosmetics":
                    if not self.guard("read", 240):
                        return
                    qs = urllib.parse.parse_qs(parsed.query)
                    raw = ",".join(qs.get("uuids", [])).split(",")
                    uids = []
                    for part in raw:
                        part = part.strip()
                        if part:
                            uids.append(norm_uuid(part))
                    if len(uids) > MAX_UUIDS:
                        return self.error(400, "too many uuids (max %d)" % MAX_UUIDS)
                    return self.send_json(200, {"players": state.store.get_many(list(dict.fromkeys(uids)))})
                return self.error(404, "not found")
            except ValueError:
                return self.error(400, "bad request")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if not self.guard("auth", 30):
                return
            try:
                body = self.read_json()  # immer lesen, sonst bleiben Bytes auf der Verbindung liegen
                if parsed.path == "/v1/auth/challenge":
                    return self.send_json(200, {"serverId": state.new_challenge()})
                if parsed.path == "/v1/auth/verify":
                    username = body.get("username")
                    sid = body.get("serverId")
                    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", username) \
                            or not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{40}", sid):
                        return self.error(400, "bad request")
                    if not state.take_challenge(sid):
                        return self.error(401, "challenge expired, start again")
                    if state.args.insecure:
                        uid = norm_uuid(body.get("uuid", ""))  # nur für lokale Tests
                    else:
                        uid = mojang_has_joined(state, username, sid)
                        if uid is None:
                            return self.error(401, "minecraft login could not be verified")
                    return self.send_json(200, {"token": state.issue_token(uid), "uuid": uid, "expiresIn": TOKEN_TTL})
                return self.error(404, "not found")
            except (ValueError, KeyError, AttributeError):
                return self.error(400, "bad request")
            except RuntimeError:
                return self.error(503, "busy")

        def do_PUT(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/v1/cosmetics":
                return self.error(404, "not found")
            if not self.guard("write", 30):
                return
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            try:
                data = clean_cosmetics(self.read_json())
            except (ValueError, json.JSONDecodeError):
                return self.error(400, "bad request")
            state.store.put(uid, data)
            return self.send_json(200, {"ok": True})

    return Handler


def main():
    p = argparse.ArgumentParser(description="GoonClient cosmetics backend")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--db", default="goonclient.db")
    p.add_argument("--mojang", default="https://sessionserver.mojang.com", help="Basis-URL des Mojang Session-Servers")
    p.add_argument("--insecure", action="store_true", help="Mojang-Prüfung abschalten (NUR für lokale Tests)")
    p.add_argument("--trust-proxy", action="store_true", help="X-Forwarded-For eines Reverse-Proxys für das Rate-Limit nutzen")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    state = State(args)
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    httpd.daemon_threads = True
    print("GoonClient backend on http://%s:%d%s" % (args.host, args.port, "  (INSECURE test mode)" if args.insecure else ""))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
