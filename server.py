#!/usr/bin/env python3
"""
GoonClient Cosmetics-Backend (nur Python-Standardbibliothek, Python 3.9+).

Speichert pro Spieler-UUID, welche Cape, welches Badge, welches animierte Namensschild und welchen Hut, welche Flügel
und welches Accessoire er ausgerüstet hat,
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
  POST /v1/redeem/code   (Authorization: Bearer <token>) {"code": "<eingetippter Code>"} -> 200 {"ok", "id", "coins"},
                         400 ungültig, 409 schon eingelöst, 410 abgelaufen/aufgebraucht. Codes stehen in codes.json (add_code.py).
  POST /v1/redeem        (alt, Client 3.8-3.9) {"id": "<code-id>"} -> 200 {"ok": true} oder 409 (schon eingelöst)
  Freunde (alle mit Authorization: Bearer <token>):
  GET  /v1/friends                         -> {"incoming": [...], "outgoing": [...], "friends": [...]}
  POST /v1/friends/request  {"uuid"}       -> {"status": "sent" | "friends"}
  POST /v1/friends/respond  {"uuid", "accept": true|false} -> {"status": "friends" | "declined"}, 404 ohne Anfrage
  POST /v1/friends/remove   {"uuid"}       -> {"status": "removed"}
  PUT  /v1/stats            {"coins", "earned", "playSeconds", "owned": [item-ids]}
  GET  /v1/friends/profile?uuid=<uuid>     -> Stats + Cosmetics, nur für bestätigte Freunde (sonst 403)
  Website (Ordner site/ neben server.py):
  GET  /                                   -> die Website (site/index.html)
  GET  /download                           -> die neueste Client-JAR aus site/downloads/
  GET  /v1/site                            -> {"version", "file", "size", "updates": [...], "info", "codes": [...]}
  GET  /v1/update                          -> {"version", "file", "size", "sha256", "signature", "minecraft", "title", "notes", "url"}
  GET  /download/goonclient-x.y.z.jar      -> genau diese JAR (für den eingebauten Updater)
                                              (codes = in codes.json als "public" markierte Codes, nicht abgelaufen)
  Geschenke (alle mit Authorization: Bearer <token>, nur unter bestätigten Freunden):
  POST /v1/gifts/send   {"id", "to", "coins", "item"} -> {"status": "pending" | "claimed"} (wiederholbar mit derselben Id)
  GET  /v1/gifts                           -> {"incoming": [{"id","from","fromName","coins","item"}], "sent": {"<id>": claimed}}
  POST /v1/gifts/claim  {"id"}             -> {"ok": true}, 404 ohne solches Geschenk
  GET  /v1/events                          -> {"events": [...]} aus events.json (Event-Shops: Termine, Währung, Items;
                                              ohne Anmeldung, neue Termine ohne neue Client-Version)
"""
import argparse
import hashlib
import json
import os
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
MAX_BODY = 16384
MAX_UUIDS = 100
MAX_CODE_COINS = 100000
CHALLENGE_TTL = 60
TOKEN_TTL = 3600
RECORD_MAX_AGE = 60 * 24 * 3600  # 60 Tage ohne Lebenszeichen: Eintrag wird gelöscht

DEFAULTS = {
    "cape": "", "badge": "", "badgeColor": 0xFFFFFF, "badgeText": "", "badgePrefix": False,
    "tag": "", "tagColor1": 0xFFFFFF, "tagColor2": 0xFFFFFF, "tagSpeed": 0, "tagBold": False,
    "hat": "", "wings": "", "accessory": "",
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
        # 3D-Accessoires (ab Client 3.7.0); ältere Clients schicken sie nicht und bekommen leere Werte
        "hat": as_id(raw.get("hat")),
        "wings": as_id(raw.get("wings")),
        "accessory": as_id(raw.get("accessory")),
    }


ITEM_RE = re.compile(r"^[a-z]+\.[a-z0-9_]{1,24}$")
MAX_PENDING_REQUESTS = 200
MAX_OPEN_GIFTS = 50
MAX_GIFT_COINS = 10000
GIFT_ID_RE = re.compile(r"^[0-9a-f]{16,32}$")
GIFT_ITEM_RE = re.compile(r"^[a-z]+\.[a-z0-9_]{1,32}$")
MAX_OWNED = 400


def clean_stats(raw):
    """Prüft die Stats eines Spielers (Goon Coins, Spielzeit, gekaufte Items). Unbekanntes wird verworfen."""
    if not isinstance(raw, dict):
        raise ValueError("body must be a JSON object")
    owned = raw.get("owned")
    items = []
    if isinstance(owned, list):
        for it in owned[:MAX_OWNED]:
            if isinstance(it, str) and ITEM_RE.match(it) and it not in items:
                items.append(it)
    return {
        "coins": as_int(raw.get("coins"), 0, 10 ** 9, 0),
        "earned": as_int(raw.get("earned"), 0, 10 ** 9, 0),
        "playSeconds": as_int(raw.get("playSeconds"), 0, 10 ** 10, 0),
        "owned": items,
    }


def norm_uuid(text):
    return str(uuidlib.UUID(text))


class Store:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS cosmetics (uuid TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)")
        # Eingelöste Codes: pro Spieler und Code genau eine Zeile (wird nie gelöscht)
        self.db.execute("CREATE TABLE IF NOT EXISTS redeemed (uuid TEXT NOT NULL, code TEXT NOT NULL, at REAL NOT NULL, "
                        "PRIMARY KEY (uuid, code))")
        # Freunde (ab Client 3.9.0): bestätigte Namen, offene Anfragen, Freundschaften (a < b) und Stats
        self.db.execute("CREATE TABLE IF NOT EXISTS names (uuid TEXT PRIMARY KEY, name TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS friend_requests (src TEXT NOT NULL, dst TEXT NOT NULL, at REAL NOT NULL, "
                        "PRIMARY KEY (src, dst))")
        self.db.execute("CREATE TABLE IF NOT EXISTS friendships (a TEXT NOT NULL, b TEXT NOT NULL, since REAL NOT NULL, "
                        "PRIMARY KEY (a, b))")
        self.db.execute("CREATE TABLE IF NOT EXISTS stats (uuid TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)")
        # Geschenke (ab Client 3.48.0): Id kommt vom Sender, damit er nach einem Datenverlust erneut schicken kann
        self.db.execute("CREATE TABLE IF NOT EXISTS gifts (id TEXT PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, "
                        "coins INTEGER NOT NULL, item TEXT NOT NULL, at REAL NOT NULL, claimed REAL)")
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

    def claim_count(self, code):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM redeemed WHERE code=?", (code,)).fetchone()[0]

    def claim(self, uid, code):
        """Merkt sich, dass `uid` den Code `code` eingelöst hat. False, wenn das schon vorher geschehen ist."""
        with self.lock:
            cur = self.db.execute("INSERT OR IGNORE INTO redeemed(uuid, code, at) VALUES(?,?,?)", (uid, code, time.time()))
            self.db.commit()
            return cur.rowcount == 1

    # ---------- Freunde ----------

    def set_name(self, uid, name):
        with self.lock:
            self.db.execute("INSERT INTO names(uuid, name) VALUES(?,?) ON CONFLICT(uuid) DO UPDATE SET name=excluded.name",
                            (uid, name))
            self.db.commit()

    def _name(self, uid):
        row = self.db.execute("SELECT name FROM names WHERE uuid=?", (uid,)).fetchone()
        return row[0] if row else ""

    def are_friends(self, x, y):
        a, b = sorted((x, y))
        with self.lock:
            return self.db.execute("SELECT 1 FROM friendships WHERE a=? AND b=?", (a, b)).fetchone() is not None

    def _befriend(self, x, y):
        a, b = sorted((x, y))
        self.db.execute("INSERT OR IGNORE INTO friendships(a, b, since) VALUES(?,?,?)", (a, b, time.time()))
        self.db.execute("DELETE FROM friend_requests WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (x, y, y, x))

    def request_friend(self, src, dst):
        """Schickt eine Anfrage. Hat dst schon an src angefragt, werden beide sofort Freunde. Gibt den Status zurück."""
        a, b = sorted((src, dst))
        with self.lock:
            if self.db.execute("SELECT 1 FROM friendships WHERE a=? AND b=?", (a, b)).fetchone():
                return "friends"
            if self.db.execute("SELECT 1 FROM friend_requests WHERE src=? AND dst=?", (dst, src)).fetchone():
                self._befriend(src, dst)
                self.db.commit()
                return "friends"
            pending = self.db.execute("SELECT COUNT(*) FROM friend_requests WHERE src=?", (src,)).fetchone()[0]
            if pending >= MAX_PENDING_REQUESTS:
                raise RuntimeError("too many pending friend requests")
            self.db.execute("INSERT OR IGNORE INTO friend_requests(src, dst, at) VALUES(?,?,?)", (src, dst, time.time()))
            self.db.commit()
            return "sent"

    def respond_friend(self, me, other, accept):
        """Antwort auf eine Anfrage von `other`. None, wenn es keine solche Anfrage gibt."""
        with self.lock:
            if not self.db.execute("SELECT 1 FROM friend_requests WHERE src=? AND dst=?", (other, me)).fetchone():
                return None
            if accept:
                self._befriend(me, other)
            else:
                self.db.execute("DELETE FROM friend_requests WHERE src=? AND dst=?", (other, me))
            self.db.commit()
            return "friends" if accept else "declined"

    def remove_friend(self, me, other):
        a, b = sorted((me, other))
        with self.lock:
            self.db.execute("DELETE FROM friendships WHERE a=? AND b=?", (a, b))
            self.db.execute("DELETE FROM friend_requests WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (me, other, other, me))
            self.db.commit()

    def friends_overview(self, me):
        with self.lock:
            incoming = [{"uuid": r[0], "name": self._name(r[0]), "at": int(r[1] * 1000)} for r in
                        self.db.execute("SELECT src, at FROM friend_requests WHERE dst=? ORDER BY at", (me,)).fetchall()]
            outgoing = [{"uuid": r[0], "name": self._name(r[0])} for r in
                        self.db.execute("SELECT dst FROM friend_requests WHERE src=?", (me,)).fetchall()]
            friends = []
            for a, b, since in self.db.execute("SELECT a, b, since FROM friendships WHERE a=? OR b=?", (me, me)).fetchall():
                other = b if a == me else a
                friends.append({"uuid": other, "name": self._name(other), "since": int(since * 1000)})
        return {"incoming": incoming, "outgoing": outgoing, "friends": friends}

    # ---------- Geschenke ----------

    def send_gift(self, src, gid, dst, coins, item):
        """Legt ein Geschenk an (wiederholbar mit derselben Id). Gibt "pending"/"claimed" zurück, None bei fremder Id."""
        with self.lock:
            row = self.db.execute("SELECT src, claimed FROM gifts WHERE id=?", (gid,)).fetchone()
            if row:
                return None if row[0] != src else ("claimed" if row[1] else "pending")
            open_count = self.db.execute("SELECT COUNT(*) FROM gifts WHERE src=? AND claimed IS NULL", (src,)).fetchone()[0]
            if open_count >= MAX_OPEN_GIFTS:
                raise RuntimeError("too many open gifts")
            self.db.execute("INSERT INTO gifts(id, src, dst, coins, item, at, claimed) VALUES(?,?,?,?,?,?,NULL)",
                            (gid, src, dst, coins, item, time.time()))
            self.db.commit()
            return "pending"

    def gifts_overview(self, me):
        with self.lock:
            incoming = [{"id": r[0], "from": r[1], "fromName": self._name(r[1]), "coins": r[2], "item": r[3]}
                        for r in self.db.execute("SELECT id, src, coins, item FROM gifts WHERE dst=? AND claimed IS NULL "
                                                 "ORDER BY at", (me,)).fetchall()]
            sent = {r[0]: r[1] is not None for r in self.db.execute(
                "SELECT id, claimed FROM gifts WHERE src=? AND at > ?", (me, time.time() - 30 * 86400)).fetchall()}
        return {"incoming": incoming, "sent": sent}

    def claim_gift(self, me, gid):
        """Empfänger bestätigt ein Geschenk. False, wenn es kein Geschenk an ihn mit dieser Id gibt."""
        with self.lock:
            row = self.db.execute("SELECT 1 FROM gifts WHERE id=? AND dst=?", (gid, me)).fetchone()
            if not row:
                return False
            self.db.execute("UPDATE gifts SET claimed=? WHERE id=? AND claimed IS NULL", (time.time(), gid))
            self.db.commit()
            return True

    def put_stats(self, uid, data):
        with self.lock:
            self.db.execute("INSERT INTO stats(uuid, data, updated) VALUES(?,?,?) "
                            "ON CONFLICT(uuid) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                            (uid, json.dumps(data), time.time()))
            self.db.commit()

    def friend_profile(self, uid):
        with self.lock:
            st = self.db.execute("SELECT data, updated FROM stats WHERE uuid=?", (uid,)).fetchone()
            cos = self.db.execute("SELECT data FROM cosmetics WHERE uuid=?", (uid,)).fetchone()
            name = self._name(uid)
        stats = json.loads(st[0]) if st else None
        if stats is not None:
            stats["updated"] = int(st[1] * 1000)
        return {"uuid": uid, "name": name, "stats": stats, "cosmetics": json.loads(cos[0]) if cos else None}

    def get_many(self, uids):
        result = {}
        with self.lock:
            for uid in uids:
                row = self.db.execute("SELECT data FROM cosmetics WHERE uuid=?", (uid,)).fetchone()
                if row:
                    result[uid] = json.loads(row[0])
        return result


CODE_SALT = "goonclient-code-v1|"
CODE_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
CODE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_code(text):
    """Wie RedeemCodes.normalize im Client: nur A-Z und 0-9, großgeschrieben."""
    return "".join(ch for ch in text.upper() if ("A" <= ch <= "Z") or ("0" <= ch <= "9"))


def hash_code(normalized):
    return hashlib.sha256((CODE_SALT + normalized).encode("utf-8")).hexdigest()


class Codes:
    """
    Einlösbare Goon-Coins-Codes aus codes.json (nur Hashes, der Klartext steht nirgends). Die Datei wird bei jeder Abfrage
    auf Änderungen geprüft; neue Codes gelten also sofort, ohne Neustart und ohne neue Client-Version.
    Eintrag: {"id": "bonus3000", "hash": "<sha256>", "coins": 3000, "maxUses": 50, "expires": "2026-12-31"}
    (maxUses = höchstens so viele Spieler insgesamt, expires = letzter gültiger Tag; beide optional).
    """

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.mtime = None
        self.by_hash = {}

    def _reload(self):
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            self.by_hash, self.mtime = {}, None
            return
        if mtime == self.mtime:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            print("codes.json could not be read: %s" % e)
            return  # alte Liste behalten
        table = {}
        for c in raw.get("codes", []) if isinstance(raw, dict) else []:
            if not isinstance(c, dict):
                continue
            cid, h, coins = c.get("id"), c.get("hash"), c.get("coins")
            if not (isinstance(cid, str) and CODE_ID_RE.match(cid) and isinstance(h, str) and CODE_HASH_RE.match(h)
                    and isinstance(coins, int) and not isinstance(coins, bool) and 0 < coins <= MAX_CODE_COINS):
                print("codes.json: invalid entry skipped: %r" % (c,))
                continue
            max_uses = c.get("maxUses")
            public_code = c.get("code") if c.get("public") is True and isinstance(c.get("code"), str) \
                and hash_code(normalize_code(c.get("code"))) == h else None  # nur zeigen, wenn Klartext und Hash passen
            table[h] = {"id": cid, "coins": coins,
                        "maxUses": max_uses if isinstance(max_uses, int) and max_uses > 0 else None,
                        "expires": c.get("expires") if isinstance(c.get("expires"), str) else None,
                        "public": public_code}
        self.by_hash, self.mtime = table, mtime

    def public(self):
        """Codes, die auf der Website stehen sollen (mit Klartext), in der Reihenfolge von codes.json."""
        with self.lock:
            self._reload()
            return [e for e in self.by_hash.values() if e.get("public")]

    def find(self, text):
        normalized = normalize_code(text) if isinstance(text, str) else ""
        if not normalized or len(normalized) > 64:
            return None
        with self.lock:
            self._reload()
            return self.by_hash.get(hash_code(normalized))


class Site:
    """
    Die Website (Ordner site/ neben server.py): index.html, die neueste Client-JAR in site/downloads/ und CHANGELOG.md
    (eine Kopie der README des Clients). Beides legt der Gradle-Build nach jedem Bauen automatisch dort ab; damit ist die
    Website nach dem Hochladen immer auf dem Stand der neuesten Client-Version.
    """

    # goonclient-x.y.z.jar = Haupt-Version (Minecraft laut CHANGELOG), goonclient-x.y.z-mc26.1.2.jar = für eine andere
    # Minecraft-Version (eigenes Projekt GoonClient-26.1.2). Website und Updater bieten jede Version passend an.
    JAR_RE = re.compile(r"^goonclient-(\d+)\.(\d+)\.(\d+)(?:-mc(\d+(?:\.\d+){1,3}))?\.jar$")
    MC_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")

    def __init__(self, folder):
        self.folder = folder
        self.lock = threading.Lock()
        self.cache = {}  # Pfad -> (mtime, Inhalt)

    def _read(self, path):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None
        with self.lock:
            hit = self.cache.get(path)
            if hit and hit[0] == mtime:
                return hit[1]
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return None
        with self.lock:
            self.cache[path] = (mtime, data)
        return data

    def index(self):
        return self._read(os.path.join(self.folder, "index.html"))

    def default_minecraft(self):
        """Minecraft-Version der Haupt-JAR (ohne -mc im Namen), aus dem CHANGELOG."""
        return self.changelog(limit=1)[1].get("minecraft") or "1.21.11"

    def _jars(self):
        """Alle JARs in site/downloads: [(Dateiname, (x, y, z), Minecraft-Version)]."""
        folder = os.path.join(self.folder, "downloads")
        try:
            names = os.listdir(folder)
        except OSError:
            return []
        default = None
        out = []
        for n in names:
            m = self.JAR_RE.match(n)
            if m:
                if m.group(4) is None and default is None:
                    default = self.default_minecraft()
                out.append((n, tuple(int(x) for x in m.groups()[:3]), m.group(4) or default))
        return out

    def latest_jar(self, mc=None):
        """(Dateiname, Version) der neuesten JAR für diese Minecraft-Version (None = Haupt-Version), oder (None, None)."""
        wanted = mc if mc and self.MC_RE.match(mc) else self.default_minecraft()
        best = None
        for n, v, jmc in self._jars():
            if jmc == wanted and (best is None or v > best[1]):
                best = (n, v)
        if best is None:
            return None, None
        return best[0], "%d.%d.%d" % best[1]

    def downloads(self):
        """Neueste JAR je Minecraft-Version für die Website, neueste Minecraft-Version zuerst."""
        versions = {jmc for _, _, jmc in self._jars() if jmc}
        out = []
        for mc in versions:
            name, version = self.latest_jar(mc)
            if name:
                out.append({"minecraft": mc, "version": version, "file": name, "size": len(self.jar_bytes(name) or b""),
                            "url": "/download?mc=" + mc})
        out.sort(key=lambda d: tuple(int(x) for x in d["minecraft"].split(".")), reverse=True)
        return out

    def jar_bytes(self, name):
        return self._read(os.path.join(self.folder, "downloads", name))

    def jar_sha256(self, name):
        """SHA-256 (hex) einer JAR; wird pro Datei-Inhalt nur einmal berechnet."""
        data = self.jar_bytes(name)
        if data is None:
            return None
        key = ("sha", name, len(data), id(data))
        with self.lock:
            hit = self.cache.get(key)
        if hit is None:
            hit = hashlib.sha256(data).hexdigest()
            with self.lock:
                self.cache[key] = hit
        return hit

    def jar_signature(self, name):
        """Ed25519-Signatur (Base64) aus goonclient-x.y.z.jar.sig, die der Gradle-Build anlegt, oder None."""
        raw = self._read(os.path.join(self.folder, "downloads", name + ".sig"))
        if not raw:
            return None
        sig = raw.decode("ascii", "replace").strip()
        return sig if re.match(r"^[A-Za-z0-9+/=]{40,200}$", sig) else None

    def update_info(self, mc=None):
        """Antwort für /v1/update: was der eingebaute Updater des Clients braucht (für seine Minecraft-Version)."""
        name, version = self.latest_jar(mc)
        if not name:
            return None
        data = self.jar_bytes(name)
        if data is None:
            return None
        updates, info = self.changelog(limit=1)
        latest = updates[0] if updates and updates[0]["version"] == version else None
        return {
            "version": version,
            "file": name,
            "size": len(data),
            "sha256": self.jar_sha256(name),
            "signature": self.jar_signature(name),
            "minecraft": mc if mc and self.MC_RE.match(mc) else info.get("minecraft"),
            "title": latest["title"] if latest else "",
            "notes": (latest["body"] if latest else "")[:4000],
            "url": "/download/" + name,
        }

    def changelog(self, limit=40):
        """Die "## Update x.y.z: Titel"-Abschnitte aus CHANGELOG.md, neueste zuerst."""
        raw = self._read(os.path.join(self.folder, "CHANGELOG.md"))
        if not raw:
            return [], {}
        text = raw.decode("utf-8", "replace")
        entries = []
        current = None
        for line in text.splitlines():
            m = re.match(r"^## Update (\d+\.\d+\.\d+)\s*[:\-–]?\s*(.*)$", line)
            if m:
                current = {"version": m.group(1), "title": m.group(2).strip(), "body": []}
                entries.append(current)
            elif line.startswith("## ") or line.startswith("# "):
                current = None
            elif current is not None:
                current["body"].append(line)
        for e in entries:
            e["body"] = "\n".join(e["body"]).strip()
        entries.sort(key=lambda e: tuple(int(x) for x in e["version"].split(".")), reverse=True)
        # Versionen aus der Tabelle oben (Minecraft, Fabric API)
        info = {}
        for key, label in (("minecraft", "Minecraft"), ("fabricApi", "Fabric API"), ("fabricLoader", "Fabric Loader")):
            m = re.search(r"^\|\s*" + re.escape(label) + r"\s*\|\s*([^|]+?)\s*\|", text, re.MULTILINE)
            if m:
                info[key] = m.group(1).strip()
        return entries[:limit], info


EVENT_ID_RE = re.compile(r"^[a-z0-9_]{1,24}$")
EVENT_TEXT_RE = re.compile(r"^[\x20-\x7e]{1,24}$")
EVENT_ITEM_RE = re.compile(r"^[a-z]+\.[a-z0-9_]{1,32}$")
EVENT_THEMES = {"halloween", "winter", "default"}
MAX_EVENT_DAYS = 62


def parse_event_time(text):
    """ISO-Zeit mit Zeitzone, z.B. "2026-10-31T00:00:00+01:00", in Epoch-Millisekunden (sonst None)."""
    import datetime
    if not isinstance(text, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None  # ohne Zeitzone wäre der Zeitpunkt je nach Server verschieden
    return int(dt.timestamp() * 1000)


class Events:
    """
    Zeitlich begrenzte Event-Shops aus events.json (wie codes.json bei jeder Abfrage auf Änderungen geprüft). Eintrag:
    {"id": "halloween2026", "name": "Halloween", "currency": "halloween", "currencyName": "Halloween Coins",
     "start": "2026-10-31T00:00:00+01:00", "end": "2026-11-07T00:00:00+01:00", "endLabel": "Nov 7, 2026",
     "coinsPerMinute": 3, "color": "#FF7A1A", "theme": "halloween", "items": ["hat.jackolantern", ...]}
    Items müssen im Client als limitierte Items eingebaut sein; unbekannte Ids ignoriert der Client.
    """

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.mtime = None
        self.events = []

    def _reload(self):
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            self.events, self.mtime = [], None
            return
        if mtime == self.mtime:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            print("events.json could not be read: %s" % e)
            return  # alte Liste behalten
        out = []
        for e in raw.get("events", []) if isinstance(raw, dict) else []:
            clean = clean_event(e)
            if clean is None:
                print("events.json: invalid entry skipped: %r" % (e,))
            elif all(x["id"] != clean["id"] for x in out):
                out.append(clean)
        self.events, self.mtime = out[:8], mtime

    def all(self):
        with self.lock:
            self._reload()
            return list(self.events)


def clean_event(e):
    if not isinstance(e, dict):
        return None
    eid, cur = e.get("id"), e.get("currency")
    name, cur_name = e.get("name"), e.get("currencyName")
    if not (isinstance(eid, str) and EVENT_ID_RE.match(eid) and isinstance(cur, str) and EVENT_ID_RE.match(cur)
            and isinstance(name, str) and EVENT_TEXT_RE.match(name) and isinstance(cur_name, str) and EVENT_TEXT_RE.match(cur_name)):
        return None
    start, end = parse_event_time(e.get("start")), parse_event_time(e.get("end"))
    if start is None or end is None or end <= start or end - start > MAX_EVENT_DAYS * 86400 * 1000:
        return None
    cpm = e.get("coinsPerMinute", 3)
    if not isinstance(cpm, int) or isinstance(cpm, bool) or not 1 <= cpm <= 20:
        return None
    items = [i for i in e.get("items", []) if isinstance(i, str) and EVENT_ITEM_RE.match(i)] \
        if isinstance(e.get("items"), list) else []
    if not items:
        return None
    color = e.get("color") if isinstance(e.get("color"), str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", e.get("color")) else "#FF7A1A"
    label = e.get("endLabel") if isinstance(e.get("endLabel"), str) and EVENT_TEXT_RE.match(e.get("endLabel")) else ""
    theme = e.get("theme") if e.get("theme") in EVENT_THEMES else "default"
    return {"id": eid, "name": name, "currency": cur, "currencyName": cur_name, "startMs": start, "endMs": end,
            "endLabel": label, "coinsPerMinute": cpm, "color": color, "theme": theme, "items": list(dict.fromkeys(items))[:64]}


def code_expired(entry):
    exp = entry.get("expires")
    if not exp:
        return False
    try:
        return time.strftime("%Y-%m-%d", time.gmtime()) > exp
    except (TypeError, ValueError):
        return False


# Alte Ids (laugh, heart, cry, celebrate) bleiben erlaubt, damit ältere Clients nicht abgewiesen werden
EMOTE_IDS = {"wave", "dance", "flex", "dab", "salute", "spin", "orangejustice", "levitate",
             "laugh", "heart", "cry", "celebrate",
             # 3.44.0
             "thumbsup", "point", "shrug", "clap", "think", "facepalm", "bow", "cheer",
             # 3.45.0 (Halloween, limitiert)
             "zombie", "boo",
             # 3.49.0 (Season-Pass, limitiert)
             "robot"}
EMOTE_TTL = 8.0  # so lange bleibt ein Emote abrufbar (Sekunden)


class Emotes:
    """Das zuletzt gestartete Emote je Spieler, nur im Speicher (geht beim Neustart verloren, ist ohnehin kurzlebig)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.data = {}  # uuid -> [id, seq, startzeit]
        self.seq = 0

    def start(self, uid, emote):
        with self.lock:
            now = time.time()
            for k in [k for k, v in self.data.items() if now - v[2] > EMOTE_TTL]:
                del self.data[k]
            self.seq += 1
            self.data[uid] = [emote, self.seq, now]
            return self.seq

    def get_many(self, uids):
        out = {}
        now = time.time()
        with self.lock:
            for uid in uids:
                v = self.data.get(uid)
                if v and now - v[2] < EMOTE_TTL:
                    out[uid] = {"id": v[0], "seq": v[1], "ageMs": int((now - v[2]) * 1000)}
        return out


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
        self.emotes = Emotes()
        self.codes = Codes(args.codes)
        self.events = Events(args.events)
        self.site = Site(args.site)
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

        def send_bytes(self, data, content_type, extra=None):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        # ---------- Website ----------

        def site_route(self, path, query=""):
            """Website, Download und Website-Daten. Gibt False zurück, wenn der Pfad nicht dazugehört."""
            mc = urllib.parse.parse_qs(query).get("mc", [None])[0]  # Minecraft-Version (sonst die Haupt-Version)
            if path in ("/", "/index.html"):
                html = state.site.index()
                if html is None:
                    self.error(404, "website not installed (site/index.html missing)")
                else:
                    self.send_bytes(html, "text/html; charset=utf-8", {"Cache-Control": "no-cache"})
                return True
            if path == "/download":
                if not self.guard("download", 30):
                    return True
                name, version = state.site.latest_jar(mc)
                data = state.site.jar_bytes(name) if name else None
                if data is None:
                    self.error(404, "no client build available yet" + (" for Minecraft " + mc if mc else ""))
                else:
                    self.send_bytes(data, "application/java-archive",
                                    {"Content-Disposition": 'attachment; filename="%s"' % name, "Cache-Control": "no-cache"})
                return True
            if path.startswith("/download/"):
                # genau diese Datei (der Updater lädt die Version, deren Prüfsumme er bekommen hat)
                if not self.guard("download", 30):
                    return True
                name = path[len("/download/"):]
                data = state.site.jar_bytes(name) if Site.JAR_RE.match(name) else None
                if data is None:
                    self.error(404, "no such client build")
                else:
                    self.send_bytes(data, "application/java-archive",
                                    {"Content-Disposition": 'attachment; filename="%s"' % name, "Cache-Control": "no-cache"})
                return True
            if path == "/v1/update":
                if not self.guard("update", 60):
                    return True
                info = state.site.update_info(mc)
                if info is None:
                    self.error(404, "no client build available yet")
                else:
                    self.send_json(200, info)
                return True
            if path == "/v1/events":
                if not self.guard("events", 60):
                    return True
                self.send_json(200, {"events": state.events.all()})
                return True
            if path == "/v1/site":
                if not self.guard("site", 120):
                    return True
                name, version = state.site.latest_jar()
                updates, info = state.site.changelog()
                codes = []
                for e in state.codes.public():
                    used = state.store.claim_count(e["id"])
                    left = None if e["maxUses"] is None else max(0, e["maxUses"] - used)
                    if code_expired(e) or left == 0:
                        continue  # abgelaufene oder aufgebrauchte Codes nicht mehr zeigen
                    codes.append({"code": e["public"], "coins": e["coins"], "expires": e["expires"], "usesLeft": left,
                                  "redeemed": used})
                size = len(state.site.jar_bytes(name) or b"") if name else 0
                self.send_json(200, {"version": version, "file": name, "size": size, "updates": updates,
                                     "info": info, "codes": codes, "downloads": state.site.downloads()})
                return True
            return False

        def do_HEAD(self):
            parsed = urllib.parse.urlparse(self.path)
            if not self.site_route(parsed.path, parsed.query):
                self.error(404, "not found")

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
                if self.site_route(parsed.path, parsed.query):
                    return
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
                if parsed.path == "/v1/emotes":
                    if not self.guard("emotes", 600):
                        return
                    qs = urllib.parse.parse_qs(parsed.query)
                    raw = ",".join(qs.get("uuids", [])).split(",")
                    uids = [norm_uuid(p.strip()) for p in raw if p.strip()]
                    if len(uids) > MAX_UUIDS:
                        return self.error(400, "too many uuids (max %d)" % MAX_UUIDS)
                    return self.send_json(200, {"players": state.emotes.get_many(list(dict.fromkeys(uids)))})
                if parsed.path == "/v1/gifts":
                    if not self.guard("friends", 240):
                        return
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    return self.send_json(200, state.store.gifts_overview(uid))
                if parsed.path in ("/v1/friends", "/v1/friends/profile"):
                    if not self.guard("friends", 240):
                        return
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    if parsed.path == "/v1/friends":
                        return self.send_json(200, state.store.friends_overview(uid))
                    other = norm_uuid(urllib.parse.parse_qs(parsed.query).get("uuid", [""])[0])
                    if other != uid and not state.store.are_friends(uid, other):
                        return self.error(403, "only friends can see stats")
                    return self.send_json(200, state.store.friend_profile(other))
                return self.error(404, "not found")
            except ValueError:
                return self.error(400, "bad request")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            is_emote = parsed.path == "/v1/emote"
            is_redeem = parsed.path in ("/v1/redeem", "/v1/redeem/code")
            is_friends = parsed.path.startswith("/v1/friends/")
            is_gift = parsed.path in ("/v1/gifts/send", "/v1/gifts/claim")
            group, limit = ("emote", 60) if is_emote else ("redeem", 20) if is_redeem \
                else ("friends_write", 60) if is_friends else ("gifts", 120) if is_gift else ("auth", 30)
            if not self.guard(group, limit):
                return
            try:
                body = self.read_json()  # immer lesen, sonst bleiben Bytes auf der Verbindung liegen
                if is_friends:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    other = norm_uuid(body.get("uuid", ""))
                    if other == uid:
                        return self.error(400, "that is you")
                    if parsed.path == "/v1/friends/request":
                        return self.send_json(200, {"status": state.store.request_friend(uid, other)})
                    if parsed.path == "/v1/friends/respond":
                        status = state.store.respond_friend(uid, other, body.get("accept") is True)
                        if status is None:
                            return self.error(404, "no such friend request")
                        return self.send_json(200, {"status": status})
                    if parsed.path == "/v1/friends/remove":
                        state.store.remove_friend(uid, other)
                        return self.send_json(200, {"status": "removed"})
                    return self.error(404, "not found")
                if is_gift:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    gid = body.get("id")
                    if not isinstance(gid, str) or not GIFT_ID_RE.match(gid):
                        return self.error(400, "bad gift id")
                    if parsed.path == "/v1/gifts/claim":
                        if not state.store.claim_gift(uid, gid):
                            return self.error(404, "no such gift")
                        return self.send_json(200, {"ok": True})
                    to = norm_uuid(body.get("to", ""))
                    coins, item = body.get("coins", 0), body.get("item", "")
                    if to == uid:
                        return self.error(400, "that is you")
                    if not isinstance(coins, int) or isinstance(coins, bool) or not 0 <= coins <= MAX_GIFT_COINS \
                            or not isinstance(item, str) or (item and not GIFT_ITEM_RE.match(item)) or (coins > 0) == bool(item):
                        return self.error(400, "bad gift")
                    if not state.store.are_friends(uid, to):
                        return self.error(403, "only friends can get gifts")
                    status = state.store.send_gift(uid, gid, to, coins, item)
                    if status is None:
                        return self.error(409, "gift id already used")
                    return self.send_json(200, {"status": status})
                if parsed.path == "/v1/redeem/code":
                    # Neuer Weg (ab Client 3.10.0): der Spieler schickt den eingetippten Code, das Backend prüft ihn
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    entry = state.codes.find(body.get("code"))
                    if entry is None:
                        return self.error(400, "invalid code")
                    if code_expired(entry):
                        return self.error(410, "code expired")
                    if entry["maxUses"] is not None and state.store.claim_count(entry["id"]) >= entry["maxUses"]:
                        return self.error(410, "code used up")
                    if not state.store.claim(uid, entry["id"]):
                        return self.error(409, "already redeemed")
                    return self.send_json(200, {"ok": True, "id": entry["id"], "coins": entry["coins"]})
                if is_redeem:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    code = body.get("id")
                    if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]{1,32}", code):
                        return self.error(400, "bad code id")
                    if not state.store.claim(uid, code):
                        return self.error(409, "already redeemed")
                    return self.send_json(200, {"ok": True})
                if is_emote:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    emote = body.get("id")
                    if not isinstance(emote, str) or emote not in EMOTE_IDS:
                        return self.error(400, "unknown emote")
                    return self.send_json(200, {"ok": True, "seq": state.emotes.start(uid, emote)})
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
                    state.store.set_name(uid, username)  # von Mojang bestätigter Name, für Freundesanfragen
                    return self.send_json(200, {"token": state.issue_token(uid), "uuid": uid, "expiresIn": TOKEN_TTL})
                return self.error(404, "not found")
            except (ValueError, KeyError, AttributeError):
                return self.error(400, "bad request")
            except RuntimeError:
                return self.error(503, "busy")

        def do_PUT(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path not in ("/v1/cosmetics", "/v1/stats"):
                return self.error(404, "not found")
            if not self.guard("write", 30):
                return
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            try:
                if parsed.path == "/v1/stats":
                    state.store.put_stats(uid, clean_stats(self.read_json()))
                else:
                    state.store.put(uid, clean_cosmetics(self.read_json()))
            except (ValueError, json.JSONDecodeError):
                return self.error(400, "bad request")
            return self.send_json(200, {"ok": True})

    return Handler


def main():
    p = argparse.ArgumentParser(description="GoonClient cosmetics backend")
    # Auf Render (oder anderen Hostern mit $PORT) reicht "python server.py" ohne weitere Angaben
    p.add_argument("--host", default="0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    p.add_argument("--db", default="goonclient.db")
    p.add_argument("--codes", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "codes.json"),
                   help="Datei mit den einlösbaren Codes (Standard: codes.json neben server.py)")
    p.add_argument("--events", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.json"),
                   help="Datei mit den Event-Shops (Standard: events.json neben server.py)")
    p.add_argument("--site", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "site"),
                   help="Ordner der Website (Standard: site/ neben server.py)")
    p.add_argument("--mojang", default="https://sessionserver.mojang.com", help="Basis-URL des Mojang Session-Servers")
    p.add_argument("--insecure", action="store_true", help="Mojang-Prüfung abschalten (NUR für lokale Tests)")
    p.add_argument("--trust-proxy", action="store_true", help="X-Forwarded-For eines Reverse-Proxys für das Rate-Limit nutzen")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    if os.environ.get("RENDER") and not args.trust_proxy:
        # Auf Render kommen alle Anfragen über deren Proxy: ohne X-Forwarded-For teilen sich ALLE Spieler ein Limit
        # (dann bekommt bei mehreren Spielern jeder "too many requests" und Emotes/Accessoires kommen nicht an)
        args.trust_proxy = True
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
