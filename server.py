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

Daten behalten ohne dauerhafte Festplatte (z.B. Render Free): Umgebungsvariablen GOON_BACKUP_REPO ("name/repo", muss PRIVAT sein)
und GOON_BACKUP_TOKEN setzen. Dann wird die Datenbank alle 2 Minuten und beim Beenden gesichert und beim Start zurückgeholt (Klasse DbBackup).

Schnittstelle (alles JSON):
  GET  /v1/health                              -> {"ok", "backup": {"state": "off"|"ok"|"failing"|"blocked", "lastUpload"}}
  POST /v1/auth/challenge                      -> {"serverId": "..."}
  POST /v1/auth/verify   {"username","serverId"} -> {"token","uuid","expiresIn"}
  PUT  /v1/cosmetics     (Authorization: Bearer <token>) Body: Cosmetics-Objekt
  GET  /v1/cosmetics?uuids=<uuid>,<uuid>,...   (höchstens 100) -> {"players": {"<uuid>": Cosmetics-Objekt}, "active": ["<uuid>", ...]}
       ("active" = hat in den letzten 15 Minuten hochgeladen, spielt also gerade mit GoonClient)
  POST /v1/redeem/code   (Authorization: Bearer <token>) {"code": "<eingetippter Code>"} -> 200 {"ok", "id", "coins"},
                         400 ungültig, 409 schon eingelöst, 410 abgelaufen/aufgebraucht. Codes stehen in codes.json (add_code.py) und gelten höchstens 7 Tage.
  POST /v1/redeem        (alt, Client 3.8-3.9) {"id": "<code-id>"} -> 200 {"ok": true} oder 409 (schon eingelöst)
  Freunde (alle mit Authorization: Bearer <token>):
  GET  /v1/friends                         -> {"incoming": [...], "outgoing": [...], "friends": [...]}
  POST /v1/friends/request  {"uuid"}       -> {"status": "sent" | "friends"}
  POST /v1/friends/respond  {"uuid", "accept": true|false} -> {"status": "friends" | "declined"}, 404 ohne Anfrage
  POST /v1/friends/remove   {"uuid"}       -> {"status": "removed"}
  PUT  /v1/stats            {"coins", "earned", "playSeconds", "owned": [item-ids]}
  GET  /v1/friends/profile?uuid=<uuid>     -> Stats + Cosmetics, nur für bestätigte Freunde (sonst 403)
  Chat (ab Client 3.83.0; nur zwischen bestätigten Freunden, der Absender kommt immer aus dem Token):
  GET  /v1/chat/poll?boot=&since=&wait=    -> Live-Kanal per Long-Polling: {"boot","seq","resync","events":[...]}
  GET  /v1/chat/sync                       -> alle noch nicht zugestellten Nachrichten an mich
  GET  /v1/chat/state                      -> Freunde mit Status, Ungelesen-Zahl und letzter Nachricht, blockierte Spieler
  GET  /v1/chat/history?with=&before=&limit= -> Verlauf mit einem Freund, neueste zuerst
  POST /v1/chat/send      {"to","text"|"sticker","cid"} -> die gespeicherte Nachricht
  POST /v1/chat/read      {"with","upto"}   POST /v1/chat/delete {"id"}   POST /v1/chat/typing {"to"}
  POST /v1/chat/presence  {"mode": "online"|"away"|"hidden"}
  POST /v1/chat/block     {"uuid","blocked"}   POST /v1/chat/report {"with","id"}
  GET  /v1/admin/reports  (Authorization: Bearer <GOON_ADMIN_TOKEN>) -> Meldungen; ohne gesetztes Token gibt es den Endpunkt nicht
  POST /v1/admin/reset    (Admin-Token) {"uuid" oder "name", "reason"} -> GoonClient-Daten EINES Spielers zurücksetzen lassen
  GET  /v1/admin/resets   (Admin-Token) -> offene und erledigte Resets
  POST /v1/admin/reset/cancel (Admin-Token) {"id"} -> offenen Reset zurücknehmen
  GET  /v1/account/reset  (eingeloggt) -> {"reset": <id> oder null}: ein Admin hat einen Reset für mich angelegt
  POST /v1/account/reset/ack (eingeloggt) {"id"} -> Client hat den Reset ausgeführt
  Admin-Befehle (ab Client 3.99.0), nur für Konten in ADMIN_UUIDS (Absender immer aus dem Sitzungstoken):
  GET  /v1/admin/me          (eingeloggt) -> {"admin": bool}
  POST /v1/admin/command     (eingeloggt, Admin) {"command": "give"|"del", "args": {...}} -> Ergebnis
  GET  /v1/admin/history     (eingeloggt, Admin) -> eigene Anpassungen mit Status
  GET  /v1/adjustments       (eingeloggt) -> offene Anpassungen (Geschenke/Abzüge) für mich
  POST /v1/adjustments/delivered {"id"} -> Geschenk liegt beim Spieler
  POST /v1/adjustments/applied   {"id", "amount"} -> angewendet (tatsächlicher Betrag)
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
import gzip
import hashlib
import json
import os
import re
import secrets
import signal
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid as uuidlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ID_RE = re.compile(r"^[a-z0-9_]{0,24}$")
MAX_BODY = 16384
# Admin-Befehle: Obergrenzen (siehe ADMIN_COMMANDS)
ADMIN_MAX_AMOUNT = 1_000_000          # pro Befehl
ADMIN_DAILY_AMOUNT = 10_000_000       # pro Admin und Tag (Summe aller Beträge)
ADMIN_COMMANDS_PER_MINUTE = 30
ADMIN_MESSAGE_MAX = 80
ADJUST_TTL_DEFAULT = 30 * 86400       # offene Anpassungen verfallen nach 30 Tagen
ADJ_ID_RE = re.compile(r"^adj_[0-9a-f]{16}$")
MAX_UUIDS = 100
MAX_CODE_COINS = 100000
CHALLENGE_TTL = 60
TOKEN_TTL = 3600
RECORD_MAX_AGE = 60 * 24 * 3600  # 60 Tage ohne Lebenszeichen: Eintrag wird gelöscht
AURA_STYLE_DEFAULT = 100 | 100 << 8 | 100 << 16  # Aura: 100 % Dichte, Größe und Tempo, keine eigenen Farben
PET_STYLE_DEFAULT = 120 | 100 << 8 | 1 << 16  # Haustier: 120 % Größe, 100 % Animation, Effekte an
ACTIVE_MAX_AGE = 15 * 60  # Clients laden alle 5 Minuten hoch: so lange gilt ein Spieler als aktiver GoonClient-Nutzer

DEFAULTS = {
    "cape": "", "badge": "", "badgeColor": 0xFFFFFF, "badgeText": "", "badgePrefix": False,
    "tag": "", "tagColor1": 0xFFFFFF, "tagColor2": 0xFFFFFF, "tagSpeed": 0, "tagBold": False,
    "hat": "", "wings": "", "accessory": "", "pet": "", "aura": "",
    "auraStyle": AURA_STYLE_DEFAULT, "auraColor1": 0xFFFFFF, "auraColor2": 0xFFFFFF,
    "petStyle": PET_STYLE_DEFAULT,
    "font": "",
    "mount": "",
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
        "pet": as_id(raw.get("pet")),
        "aura": as_id(raw.get("aura")),
        # Aura-Einstellungen (ab Client 3.59.0): Dichte | Größe << 8 | Tempo << 16 | eigene Farben << 24
        "auraStyle": clean_aura_style(raw.get("auraStyle")),
        "auraColor1": as_int(raw.get("auraColor1"), 0, 0xFFFFFF, 0xFFFFFF),
        "auraColor2": as_int(raw.get("auraColor2"), 0, 0xFFFFFF, 0xFFFFFF),
        # Haustier-Einstellungen (ab Client 3.60.0): Größe | Animation << 8 | Effekte << 16
        "petStyle": clean_pet_style(raw.get("petStyle")),
        # Schrift des Namens (ab Client 3.61.0); ältere Clients schicken sie nicht und bekommen ""
        "font": as_id(raw.get("font")),
        "mount": as_id(raw.get("mount")),
    }


def clean_pet_style(value):
    """Wie CosmeticsPayload.packPetStyle: Größe 50-200 %, Animation 0-150 %, Bit 16 = Effekte, Bits 17-18 = Variante 0-2."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return PET_STYLE_DEFAULT
    size = max(50, min(200, value & 0xFF))
    anim = max(0, min(150, (value >> 8) & 0xFF))
    variant = min(2, (value >> 17) & 3)
    return size | anim << 8 | ((value >> 16) & 1) << 16 | variant << 17


def clean_aura_style(value):
    """Wie CosmeticsPayload.packAuraStyle: Dichte 25-200, Größe 50-200, Tempo 25-200 (Prozent), Bit 24 = eigene Farben."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return AURA_STYLE_DEFAULT
    intensity = max(25, min(200, value & 0xFF))
    size = max(50, min(200, (value >> 8) & 0xFF))
    speed = max(25, min(200, (value >> 16) & 0xFF))
    return intensity | size << 8 | speed << 16 | ((value >> 24) & 1) << 24


ITEM_RE = re.compile(r"^[a-z]+\.[a-z0-9_]{1,24}$")
MAX_PENDING_REQUESTS = 200
MAX_FRIENDS = 100
MAX_REQUESTS_PER_DAY = 20
CHAT_MAX_TEXT = 300
CHAT_KEEP_PER_CONVERSATION = 200
CHAT_TTL_DEFAULT = 7 * 86400
REPORT_MESSAGES = 20
REPORT_TTL = 90 * 86400
STICKER_RE = re.compile(r"[a-z0-9_.]{1,40}")
CID_RE = re.compile(r"[A-Za-z0-9_-]{1,40}")
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


BACKUP_TAG = "goon-backup"
BACKUP_INTERVAL_DEFAULT = 120.0
BACKUP_TIMEOUT = 30
BACKUP_START_TRIES = 5
BACKUP_RETRY_SECONDS = 2
BACKUP_KEEP_LATEST = 3
BACKUP_KEEP_DAYS = 3

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
        # Chat (ab Client 3.83.0). Wer die Datenbank wechseln will, muss nur die Methoden unter "Chat" neu schreiben.
        self.db.execute("CREATE TABLE IF NOT EXISTS blocks (src TEXT NOT NULL, dst TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY (src, dst))")
        self.db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, dst TEXT NOT NULL, "
                        "text TEXT NOT NULL, sticker TEXT NOT NULL, cid TEXT NOT NULL, at REAL NOT NULL, delivered REAL, seen REAL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS messages_pair ON messages (src, dst, id)")
        self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS messages_cid ON messages (src, cid)")
        self.db.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter TEXT NOT NULL, reported TEXT NOT NULL, "
                        "message INTEGER NOT NULL, at REAL NOT NULL, excerpt TEXT NOT NULL)")
        # Admin-Anpassungen (ab Client 3.99.0): Buchungsliste für Coins (Coins selbst liegen beim Spieler) und ein Audit-Protokoll,
        # das über die API nie gelöscht werden kann
        self.db.execute("CREATE TABLE IF NOT EXISTS adjustments (id TEXT PRIMARY KEY, target TEXT NOT NULL, amount INTEGER NOT NULL, "
                        "kind TEXT NOT NULL, message TEXT NOT NULL, issuer TEXT NOT NULL, issuer_name TEXT NOT NULL, created REAL NOT NULL, "
                        "status TEXT NOT NULL, applied INTEGER, delivered_at REAL, applied_at REAL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS adjustments_target ON adjustments (target, status)")
        self.db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, actor TEXT NOT NULL, "
                        "action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL, result TEXT NOT NULL)")
        # Resets (ab Client 3.98.0): ein Admin setzt die GoonClient-Daten EINES Spielers zurück (z.B. geteiltes Modpack)
        self.db.execute("CREATE TABLE IF NOT EXISTS resets (id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT NOT NULL, reason TEXT NOT NULL, "
                        "created REAL NOT NULL, done REAL, cancelled REAL)")
        self.db.commit()
        self.chat_ttl = CHAT_TTL_DEFAULT
        self.last_chat_purge = 0.0
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
            if self._blocked(src, dst):
                return "blocked"  # man hat ihn selbst blockiert: erst aufheben
            if self.db.execute("SELECT 1 FROM friend_requests WHERE src=? AND dst=?", (dst, src)).fetchone():
                if self._friend_count(src) >= MAX_FRIENDS or self._friend_count(dst) >= MAX_FRIENDS:
                    return "full"
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
                if self._friend_count(me) >= MAX_FRIENDS or self._friend_count(other) >= MAX_FRIENDS:
                    return "full"
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
            # Der Chat endet für beide: Die Nachrichten verschwinden auch vom Server
            self.db.execute("DELETE FROM messages WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (me, other, other, me))
            self.db.commit()

    def friends_overview(self, me):
        with self.lock:
            incoming = [{"uuid": r[0], "name": self._name(r[0]), "at": int(r[1] * 1000)} for r in
                        self.db.execute("SELECT src, at FROM friend_requests WHERE dst=? AND src NOT IN "
                                        "(SELECT dst FROM blocks WHERE src=?) ORDER BY at", (me, me)).fetchall()]
            outgoing = [{"uuid": r[0], "name": self._name(r[0])} for r in
                        self.db.execute("SELECT dst FROM friend_requests WHERE src=?", (me,)).fetchall()]
            friends = []
            for a, b, since in self.db.execute("SELECT a, b, since FROM friendships WHERE a=? OR b=?", (me, me)).fetchall():
                other = b if a == me else a
                friends.append({"uuid": other, "name": self._name(other), "since": int(since * 1000)})
        return {"incoming": incoming, "outgoing": outgoing, "friends": friends}

    # ---------- Chat ----------

    def _blocked(self, src, dst):
        return self.db.execute("SELECT 1 FROM blocks WHERE src=? AND dst=?", (src, dst)).fetchone() is not None

    def _friend_count(self, uid):
        return self.db.execute("SELECT COUNT(*) FROM friendships WHERE a=? OR b=?", (uid, uid)).fetchone()[0]

    @staticmethod
    def _message_json(r):
        status = "read" if r[8] else "delivered" if r[7] else "sent"
        return {"id": r[0], "from": r[1], "to": r[2], "text": r[3], "sticker": r[4], "cid": r[5], "at": int(r[6] * 1000), "status": status}

    _COLS = "id, src, dst, text, sticker, cid, at, delivered, seen"

    def purge_chat(self, force=False):
        """Löscht Nachrichten nach Ablauf der Frist. Läuft höchstens alle paar Sekunden, die Frist gilt beim Lesen trotzdem genau."""
        now = time.time()
        if not force and now - self.last_chat_purge < min(60.0, self.chat_ttl / 2.0):
            return
        self.last_chat_purge = now
        with self.lock:
            self.db.execute("DELETE FROM messages WHERE at < ?", (now - self.chat_ttl,))
            self.db.execute("DELETE FROM reports WHERE at < ?", (now - REPORT_TTL,))
            self.db.commit()

    def send_message(self, src, dst, text, sticker, cid):
        """Speichert eine Nachricht. Gibt (Nachricht, neu?) zurück; dieselbe cid desselben Absenders ergibt keine zweite Nachricht."""
        now = time.time()
        with self.lock:
            row = self.db.execute("SELECT " + self._COLS + " FROM messages WHERE src=? AND cid=?", (src, cid)).fetchone()
            if row:
                return self._message_json(row), False
            cur = self.db.execute("INSERT INTO messages(src, dst, text, sticker, cid, at) VALUES(?,?,?,?,?,?)", (src, dst, text, sticker, cid, now))
            mid = cur.lastrowid
            # Höchstens 200 Nachrichten pro Unterhaltung
            self.db.execute("DELETE FROM messages WHERE id IN (SELECT id FROM messages WHERE (src=? AND dst=?) OR (src=? AND dst=?) "
                            "ORDER BY id DESC LIMIT -1 OFFSET ?)", (src, dst, dst, src, CHAT_KEEP_PER_CONVERSATION))
            self.db.commit()
            row = self.db.execute("SELECT " + self._COLS + " FROM messages WHERE id=?", (mid,)).fetchone()
            return self._message_json(row), True

    def history(self, me, other, before, limit):
        since = time.time() - self.chat_ttl
        with self.lock:
            rows = self.db.execute("SELECT " + self._COLS + " FROM messages WHERE ((src=? AND dst=?) OR (src=? AND dst=?)) AND id<? AND at>=? "
                                   "ORDER BY id DESC LIMIT ?", (me, other, other, me, before, since, limit)).fetchall()
        return [self._message_json(r) for r in rows]

    def take_undelivered(self, me):
        """Alle noch nicht zugestellten Nachrichten an mich; sie gelten danach als zugestellt."""
        now = time.time()
        with self.lock:
            rows = self.db.execute("SELECT " + self._COLS + " FROM messages WHERE dst=? AND delivered IS NULL AND at>=? ORDER BY id",
                                   (me, now - self.chat_ttl)).fetchall()
            self.db.execute("UPDATE messages SET delivered=? WHERE dst=? AND delivered IS NULL", (now, me))
            self.db.commit()
        return [self._message_json(r) for r in rows]

    def mark_delivered(self, me, ids):
        """Nachrichten aus dem Live-Kanal sind angekommen. Gibt [(Absender, Id)] der wirklich neu zugestellten zurück."""
        out = []
        now = time.time()
        with self.lock:
            for mid in ids:
                row = self.db.execute("SELECT src FROM messages WHERE id=? AND dst=? AND delivered IS NULL", (mid, me)).fetchone()
                if row:
                    self.db.execute("UPDATE messages SET delivered=? WHERE id=?", (now, mid))
                    out.append((row[0], mid))
            self.db.commit()
        return out

    def mark_read(self, me, other, upto):
        now = time.time()
        with self.lock:
            cur = self.db.execute("UPDATE messages SET seen=?, delivered=COALESCE(delivered, ?) WHERE src=? AND dst=? AND id<=? AND seen IS NULL",
                                  (now, now, other, me, upto))
            self.db.commit()
            return cur.rowcount

    def delete_message(self, me, mid):
        """Löscht eine eigene Nachricht. Gibt den Empfänger zurück, None, wenn es keine eigene Nachricht ist."""
        with self.lock:
            row = self.db.execute("SELECT dst FROM messages WHERE id=? AND src=?", (mid, me)).fetchone()
            if not row:
                return None
            self.db.execute("DELETE FROM messages WHERE id=?", (mid,))
            self.db.commit()
            return row[0]

    def set_block(self, me, other, blocked):
        a, b = sorted((me, other))
        with self.lock:
            if blocked:
                self.db.execute("INSERT OR IGNORE INTO blocks(src, dst, at) VALUES(?,?,?)", (me, other, time.time()))
                self.db.execute("DELETE FROM friendships WHERE a=? AND b=?", (a, b))
                self.db.execute("DELETE FROM friend_requests WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (me, other, other, me))
                self.db.execute("DELETE FROM messages WHERE (src=? AND dst=?) OR (src=? AND dst=?)", (me, other, other, me))
            else:
                self.db.execute("DELETE FROM blocks WHERE src=? AND dst=?", (me, other))
            self.db.commit()

    def chat_state(self, me):
        since = time.time() - self.chat_ttl
        friends = []
        with self.lock:
            for a, b, _ in self.db.execute("SELECT a, b, since FROM friendships WHERE a=? OR b=?", (me, me)).fetchall():
                other = b if a == me else a
                unread = self.db.execute("SELECT COUNT(*) FROM messages WHERE src=? AND dst=? AND seen IS NULL AND at>=?", (other, me, since)).fetchone()[0]
                last = self.db.execute("SELECT id, at FROM messages WHERE ((src=? AND dst=?) OR (src=? AND dst=?)) AND at>=? ORDER BY id DESC LIMIT 1",
                                       (me, other, other, me, since)).fetchone()
                friends.append({"uuid": other, "name": self._name(other), "unread": unread,
                                "lastId": last[0] if last else 0, "lastAt": int(last[1] * 1000) if last else 0})
            blocked = [{"uuid": r[0], "name": self._name(r[0])} for r in self.db.execute("SELECT dst FROM blocks WHERE src=?", (me,)).fetchall()]
        return {"friends": friends, "blocked": blocked, "maxFriends": MAX_FRIENDS}

    def add_report(self, reporter, reported, mid):
        """Speichert die letzten Nachrichten der Unterhaltung als Meldung. Gibt die Id der Meldung zurück."""
        now = time.time()
        with self.lock:
            rows = self.db.execute("SELECT " + self._COLS + " FROM messages WHERE (src=? AND dst=?) OR (src=? AND dst=?) ORDER BY id DESC LIMIT ?",
                                   (reporter, reported, reported, reporter, REPORT_MESSAGES)).fetchall()
            excerpt = [self._message_json(r) for r in reversed(rows)]
            cur = self.db.execute("INSERT INTO reports(reporter, reported, message, at, excerpt) VALUES(?,?,?,?,?)",
                                  (reporter, reported, mid, now, json.dumps(excerpt)))
            self.db.commit()
            return cur.lastrowid

    def list_reports(self, limit):
        with self.lock:
            rows = self.db.execute("SELECT id, reporter, reported, message, at, excerpt FROM reports ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [{"id": r[0], "reporter": r[1], "reporterName": self._name(r[1]), "reported": r[2], "reportedName": self._name(r[2]),
                     "message": r[3], "at": int(r[4] * 1000), "excerpt": json.loads(r[5])} for r in rows]

    # ---------- Admin-Anpassungen ----------

    def audit(self, actor, action, target, detail, result):
        with self.lock:
            self.db.execute("INSERT INTO audit(at, actor, action, target, detail, result) VALUES(?,?,?,?,?,?)",
                            (time.time(), actor, action, target, json.dumps(detail, ensure_ascii=False), result))
            self.db.commit()

    def audit_entries(self, limit=100):
        with self.lock:
            rows = self.db.execute("SELECT at, actor, action, target, detail, result FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"at": int(r[0] * 1000), "actor": r[1], "action": r[2], "target": r[3], "detail": json.loads(r[4]), "result": r[5]}
                for r in rows]

    def admin_amount_today(self, issuer):
        start = time.time() - 86400
        with self.lock:
            row = self.db.execute("SELECT COALESCE(SUM(ABS(amount)), 0) FROM adjustments WHERE issuer=? AND created > ?",
                                  (issuer, start)).fetchone()
        return int(row[0])

    def add_adjustment(self, target, amount, kind, message, issuer, issuer_name):
        aid = "adj_" + secrets.token_hex(8)
        with self.lock:
            self.db.execute("INSERT INTO adjustments(id, target, amount, kind, message, issuer, issuer_name, created, status) "
                            "VALUES(?,?,?,?,?,?,?,?, 'pending')", (aid, target, amount, kind, message, issuer, issuer_name, time.time()))
            self.db.commit()
        return aid

    def expire_adjustments(self, ttl):
        """Offene (noch nicht zugestellte) Anpassungen verfallen nach der Frist."""
        with self.lock:
            self.db.execute("UPDATE adjustments SET status='expired' WHERE status='pending' AND created < ?", (time.time() - ttl,))
            self.db.commit()

    def adjustments_for(self, target):
        """Was der Spieler noch bearbeiten muss: offene und zugestellte (noch nicht angewendete) Anpassungen."""
        with self.lock:
            rows = self.db.execute("SELECT id, amount, kind, message, issuer_name, created, status FROM adjustments "
                                   "WHERE target=? AND status IN ('pending','delivered') ORDER BY created LIMIT 100", (target,)).fetchall()
        return [{"id": r[0], "amount": abs(r[1]), "kind": r[2], "message": r[3], "from": r[4], "at": int(r[5] * 1000),
                 "status": r[6]} for r in rows]

    def mark_adjustment_delivered(self, target, aid):
        with self.lock:
            row = self.db.execute("SELECT kind, status FROM adjustments WHERE id=? AND target=?", (aid, target)).fetchone()
            if not row:
                return None
            if row[1] == "pending" and row[0] == "give":
                self.db.execute("UPDATE adjustments SET status='delivered', delivered_at=? WHERE id=?", (time.time(), aid))
                self.db.commit()
                return "delivered"
            return row[1]

    def mark_adjustment_applied(self, target, aid, amount):
        """Angewendet: bei give genau der Betrag, bei del höchstens der verlangte. Doppelte Meldungen ändern nichts."""
        with self.lock:
            row = self.db.execute("SELECT kind, status, amount FROM adjustments WHERE id=? AND target=?", (aid, target)).fetchone()
            if not row:
                return None
            kind, status, want = row
            if status not in ("pending", "delivered"):
                return status
            if kind == "give" and amount != want:
                return "bad amount"
            if kind == "del" and not 0 <= amount <= -want:
                return "bad amount"
            now = time.time()
            self.db.execute("UPDATE adjustments SET status='applied', applied=?, applied_at=?, "
                            "delivered_at=COALESCE(delivered_at, ?) WHERE id=?", (amount, now, now, aid))
            self.db.commit()
            return "applied"

    def issuer_history(self, issuer, limit=50):
        with self.lock:
            rows = self.db.execute("SELECT id, target, amount, kind, message, created, status, applied FROM adjustments "
                                   "WHERE issuer=? ORDER BY created DESC LIMIT ?", (issuer, limit)).fetchall()
            return [{"id": r[0], "target": r[1], "targetName": self._name(r[1]), "amount": abs(r[2]), "kind": r[3], "message": r[4],
                     "at": int(r[5] * 1000), "status": r[6], "applied": r[7]} for r in rows]

    # ---------- Resets einzelner Spieler ----------

    def uuids_named(self, name):
        """Alle bekannten (von Mojang bestätigten) UUIDs mit diesem Namen, ohne Groß/Klein."""
        with self.lock:
            return [r[0] for r in self.db.execute("SELECT uuid FROM names WHERE lower(name)=lower(?)", (name,)).fetchall()]

    def add_reset(self, uid, reason):
        """Legt einen Reset für genau diesen Spieler an (oder gibt den offenen zurück) und räumt NUR seine Daten auf dem Server
        auf: angezeigte Cosmetics, Stats und eigene offene Freundschaftsanfragen. Freundschaften, Chats, Geschenke bleiben."""
        with self.lock:
            row = self.db.execute("SELECT id FROM resets WHERE uuid=? AND done IS NULL AND cancelled IS NULL", (uid,)).fetchone()
            if row:
                rid = row[0]
            else:
                rid = self.db.execute("INSERT INTO resets(uuid, reason, created) VALUES(?,?,?)", (uid, reason, time.time())).lastrowid
            self.db.execute("DELETE FROM cosmetics WHERE uuid=?", (uid,))
            self.db.execute("DELETE FROM stats WHERE uuid=?", (uid,))
            self.db.execute("DELETE FROM friend_requests WHERE src=?", (uid,))
            self.db.commit()
            return rid

    def pending_reset(self, uid):
        with self.lock:
            row = self.db.execute("SELECT id FROM resets WHERE uuid=? AND done IS NULL AND cancelled IS NULL ORDER BY id LIMIT 1",
                                  (uid,)).fetchone()
            return row[0] if row else None

    def ack_reset(self, uid, rid):
        """Der Spieler meldet: Reset ausgeführt. Nur seine eigenen Resets."""
        with self.lock:
            cur = self.db.execute("UPDATE resets SET done=? WHERE id=? AND uuid=? AND done IS NULL AND cancelled IS NULL",
                                  (time.time(), rid, uid))
            self.db.commit()
            return cur.rowcount == 1

    def cancel_reset(self, rid):
        with self.lock:
            cur = self.db.execute("UPDATE resets SET cancelled=? WHERE id=? AND done IS NULL AND cancelled IS NULL", (time.time(), rid))
            self.db.commit()
            return cur.rowcount == 1

    def list_resets(self, limit):
        with self.lock:
            rows = self.db.execute("SELECT id, uuid, reason, created, done, cancelled FROM resets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [{"id": r[0], "uuid": r[1], "name": self._name(r[1]), "reason": r[2], "created": int(r[3] * 1000),
                     "state": "done" if r[4] else "cancelled" if r[5] else "pending"} for r in rows]

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

    def active_among(self, uids, max_age=ACTIVE_MAX_AGE):
        """Wer von diesen Spielern hat kürzlich hochgeladen (= spielt gerade mit GoonClient)?"""
        since = time.time() - max_age
        with self.lock:
            return [uid for uid in uids
                    if self.db.execute("SELECT 1 FROM cosmetics WHERE uuid=? AND updated>=?", (uid, since)).fetchone()]


CODE_SALT = "goonclient-code-v1|"
CODE_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
ITEM_ID_RE = re.compile(r"^[a-z]{1,16}\.[a-z0-9_]{1,32}$")  # Shop-Id, z.B. accessory.hackerorbit
CODE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_CURRENCY_RE = re.compile(r"^[a-z0-9_]{1,24}$")


def normalize_code(text):
    """Wie RedeemCodes.normalize im Client: nur A-Z und 0-9, großgeschrieben."""
    return "".join(ch for ch in text.upper() if ("A" <= ch <= "Z") or ("0" <= ch <= "9"))


def hash_code(normalized):
    return hashlib.sha256((CODE_SALT + normalized).encode("utf-8")).hexdigest()


CODE_DAYS = 7
CODE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class Codes:
    """
    Einlösbare Goon-Coins-Codes aus codes.json (nur Hashes, der Klartext steht nirgends). Die Datei wird bei jeder Abfrage
    auf Änderungen geprüft; neue Codes gelten also sofort, ohne Neustart und ohne neue Client-Version.
    Eintrag: {"id": "bonus3000", "hash": "<sha256>", "coins": 3000, "maxUses": 50, "expires": "2026-12-31"}
    (maxUses = höchstens so viele Spieler insgesamt, optional; expires = letzter gültiger Tag, Pflicht, siehe code_expired).
    Mit "item": "accessory.hackerorbit" gibt der Code zusätzlich ein exklusives Item (dann darf "coins" 0 sein).
    Clients vor 3.56.0 kennen keine Items: für sie gilt ein Item-Code nicht (426), damit niemand den Code ohne Item verbraucht.
    Mit "eventCoins": 500, "eventCurrency": "halloween" gibt der Code zusätzlich Event-Coins. Das können erst Clients ab 3.76.0, ältere bekommen ebenfalls 426.
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
            cid, h, coins = c.get("id"), c.get("hash"), c.get("coins", 0)
            item = c.get("item", "")
            if not (isinstance(item, str) and (item == "" or ITEM_ID_RE.match(item))):
                print("codes.json: invalid item, entry skipped: %r" % (c,))
                continue
            event_coins, event_currency = c.get("eventCoins", 0), c.get("eventCurrency", "")
            if not (isinstance(event_coins, int) and not isinstance(event_coins, bool) and 0 <= event_coins <= MAX_CODE_COINS
                    and isinstance(event_currency, str) and (event_coins == 0 or EVENT_CURRENCY_RE.match(event_currency))):
                print("codes.json: invalid event coins, entry skipped: %r" % (c,))
                continue
            if not (isinstance(cid, str) and CODE_ID_RE.match(cid) and isinstance(h, str) and CODE_HASH_RE.match(h)
                    and isinstance(coins, int) and not isinstance(coins, bool) and 0 <= coins <= MAX_CODE_COINS
                    and (coins > 0 or item or event_coins > 0)):
                print("codes.json: invalid entry skipped: %r" % (c,))
                continue
            max_uses = c.get("maxUses")
            public_code = c.get("code") if c.get("public") is True and isinstance(c.get("code"), str) \
                and hash_code(normalize_code(c.get("code"))) == h else None  # nur zeigen, wenn Klartext und Hash passen
            table[h] = {"id": cid, "coins": coins, "item": item, "eventCoins": event_coins, "eventCurrency": event_currency,
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

    def find_id(self, cid):
        """Eintrag zu einer Code-Id (alter Einlöse-Weg), oder None."""
        with self.lock:
            self._reload()
            for e in self.by_hash.values():
                if e["id"] == cid:
                    return e
        return None


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


def code_expired(entry, now=None):
    """
    Codes laufen spätestens nach CODE_DAYS Tagen ab. Die Datei speichert nur den letzten gültigen Tag (UTC): Fehlt er, ist er
    ungültig oder liegt er weiter als CODE_DAYS Tage in der Zukunft, gilt der Code als abgelaufen. So kann kein Code länger leben.
    """
    now = time.time() if now is None else now
    exp = entry.get("expires")
    if not isinstance(exp, str) or not CODE_DATE_RE.fullmatch(exp):
        return True
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    latest = time.strftime("%Y-%m-%d", time.gmtime(now + CODE_DAYS * 86400))
    return today > exp or exp > latest


# Alte Ids (laugh, heart, cry, celebrate) bleiben erlaubt, damit ältere Clients nicht abgewiesen werden
EMOTE_IDS = {"wave", "dance", "flex", "dab", "salute", "spin", "orangejustice", "levitate",
             "laugh", "heart", "cry", "celebrate",
             # 3.44.0
             "thumbsup", "point", "shrug", "clap", "think", "facepalm", "bow", "cheer",
             # 3.45.0 (Halloween, limitiert)
             "zombie", "boo",
             # 3.49.0 (Season-Pass, limitiert)
             "robot",
             # 3.70.0
             "heartbeat", "hero", "sleep", "meditate", "rage", "tinyhead", "confetti", "bounce", "balloon",
             "ghostly", "bighead", "flip", "fire", "mindblown"}
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


class ChatHub:
    """
    Der Live-Kanal: Je Spieler eine kurze Warteschlange im Speicher, aus der sein Long-Poll liest. Geht sie verloren (Neustart,
    neue boot-Id) oder ist sie übergelaufen, holt der Client den Stand über /v1/chat/sync nach; die Nachrichten liegen in der Datenbank.
    Long-Polling statt WebSocket, weil es ohne Zusatzpakete mit der Standardbibliothek läuft und jeder Proxy es durchlässt.
    """

    QUEUE = 300
    MAX_WAITING = 800
    ONLINE_SECONDS = 45.0

    def __init__(self):
        self.cond = threading.Condition()
        self.boot = secrets.token_hex(6)
        self.seq = 0
        self.queues = {}
        self.first = {}
        self.waiting = 0
        self.last_seen = {}
        self.modes = {}

    def publish(self, uid, event):
        with self.cond:
            self.seq += 1
            q = self.queues.setdefault(uid, [])
            q.append((self.seq, event))
            if len(q) > self.QUEUE:
                del q[0]
                self.first[uid] = q[0][0]
            self.cond.notify_all()

    def wait(self, uid, boot, since, timeout):
        """Wartet höchstens timeout Sekunden auf Neues. Gibt (seq, resync, events) zurück, None, wenn zu viele warten."""
        deadline = time.time() + timeout
        with self.cond:
            self.last_seen[uid] = time.time()
            if boot != self.boot or since < self.first.get(uid, 0) - 1:
                return self.seq, True, []
            if self.waiting >= self.MAX_WAITING:
                return None
            self.waiting += 1
            try:
                while True:
                    q = self.queues.get(uid, [])
                    fresh = [e for s, e in q if s > since]
                    if fresh:
                        self.queues[uid] = [(s, e) for s, e in q if s > since]
                        return self.seq, False, fresh
                    left = deadline - time.time()
                    if left <= 0:
                        return self.seq, False, []
                    self.cond.wait(left)
            finally:
                self.waiting -= 1
                self.last_seen[uid] = time.time()

    def set_mode(self, uid, mode):
        with self.cond:
            self.modes[uid] = mode
            self.last_seen[uid] = time.time()

    def presence(self, uid):
        """online, away oder offline. Wer "hidden" gewählt hat, wirkt offline."""
        with self.cond:
            if time.time() - self.last_seen.get(uid, 0) > self.ONLINE_SECONDS:
                return "offline"
            mode = self.modes.get(uid, "online")
        return "offline" if mode == "hidden" else mode


class BackupUnreachable(Exception):
    """Die Sicherung ist gerade nicht erreichbar (Netz, GitHub-Störung): später noch einmal versuchen."""


class AccessDenied(Exception):
    """Token oder Repo stimmen nicht: Warten hilft nicht, die Einstellungen müssen geändert werden."""


class NoAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Weiterleitungen nicht folgen: Der Download-Host darf das Token nie sehen, er wird von Hand ohne Token geladen."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def backups_to_keep(names):
    """
    Welche Sicherungen bleiben: die neuesten 3 und die neueste jedes der letzten 3 Tage, an denen es welche gab.
    Der Dateiname enthält die Zeit (UTC), neuere Namen sortieren also weiter hinten.
    """
    ordered = sorted(names, reverse=True)
    keep = set(ordered[:BACKUP_KEEP_LATEST])
    days = []
    for name in ordered:
        day = name[5:13]  # goon-YYYYMMDD-...
        if day not in days:
            days.append(day)
            if len(days) <= BACKUP_KEEP_DAYS:
                keep.add(name)
    return keep


class DbBackup:
    """
    Sichert die Datenbank als gzip-Datei in den Release "goon-backup" eines PRIVATEN GitHub-Repos und holt sie beim Start zurück.
    So überlebt alles einen Deploy oder Neustart auf einem Hoster ohne dauerhafte Festplatte (Render Free): Freunde, Chats,
    Blocklisten, Meldungen, Cosmetics und eingelöste Codes.

    Oberste Regel: Eine gute Sicherung wird nie durch eine leere Datenbank ersetzt. Deshalb gilt:
    - Ist GitHub nicht erreichbar, beendet sich der Server beim Start (der Hoster startet ihn neu), statt leer loszulaufen.
    - Sind Token oder Repo falsch, läuft er weiter, damit die Website erreichbar bleibt, lädt aber nichts hoch.
      Eine Merkdatei sorgt dafür, dass die dabei entstandene leere Datenbank auch nach einem Neustart nicht als gut gilt.
    Das Token wird nie geloggt und nie an einen anderen Host geschickt.
    """

    def __init__(self, path, repo, token, api, interval):
        self.path = path
        self.repo = repo
        self.token = token
        self.api = api.rstrip("/")
        self.interval = interval
        self.state = "off" if not (repo and token) else "starting"
        self.may_upload = False
        self.last_hash = None
        self.last_ok = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.opener = urllib.request.build_opener(NoAuthOnRedirect())
        self.marker = path + ".restore-failed"

    # ---------- HTTP ----------

    def _request(self, method, url, body=None, content_type="application/json", accept="application/vnd.github+json", auth=True):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("User-Agent", "GoonClient-Backend")
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if auth:
            req.add_header("Authorization", "Bearer " + self.token)
        if body is not None:
            req.add_header("Content-Type", content_type)
        try:
            with self.opener.open(req, timeout=BACKUP_TIMEOUT) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            data = e.read()
            return e.code, data, e.headers
        except OSError as e:
            raise BackupUnreachable(type(e).__name__)

    def _json(self, method, path, body=None):
        raw = None if body is None else json.dumps(body).encode("utf-8")
        status, data, _ = self._request(method, self.api + path, raw)
        if status >= 500 or status == 429:
            raise BackupUnreachable("HTTP %d" % status)
        try:
            return status, json.loads(data) if data else {}
        except ValueError:
            raise BackupUnreachable("bad answer")

    def _release(self):
        """Der Sicherungs-Release, None = noch keiner."""
        status, data = self._json("GET", "/repos/%s/releases/tags/%s" % (self.repo, BACKUP_TAG))
        if status == 200:
            return data
        if status == 404:
            return None
        if status in (401, 403):
            raise AccessDenied("HTTP %d" % status)
        raise BackupUnreachable("HTTP %d" % status)

    def _download(self, asset_id):
        status, data, headers = self._request("GET", self.api + "/repos/%s/releases/assets/%s" % (self.repo, asset_id), accept="application/octet-stream")
        if status in (301, 302, 303, 307, 308):
            status, data, _ = self._request("GET", headers.get("Location", ""), accept="application/octet-stream", auth=False)
        if status != 200:
            raise BackupUnreachable("HTTP %d" % status)
        return data

    # ---------- Zurückholen ----------

    def restore(self):
        """Beim Start, bevor die Datenbank geöffnet wird."""
        if self.state == "off":
            print("Backup: OFF (GOON_BACKUP_REPO and GOON_BACKUP_TOKEN not set). Without a lasting disk all data is lost on restart.", flush=True)
            return
        for attempt in range(BACKUP_START_TRIES):
            try:
                self._restore_once()
                return
            except AccessDenied as e:
                # Warten hilft hier nicht. Die Website soll laufen, aber es wird nichts hochgeladen.
                self.state = "blocked"
                if not (os.path.exists(self.path) and os.path.getsize(self.path) > 0):
                    # Nur eine jetzt entstehende leere Datenbank ist verdächtig, vorhandene Daten auf einer Festplatte nicht
                    with open(self.marker, "w", encoding="utf-8") as f:
                        f.write("restore failed\n")
                print("Backup: NOT WORKING (%s). Check GOON_BACKUP_TOKEN and GOON_BACKUP_REPO. Running with an empty database, uploads are off so the saved backup stays safe." % e, flush=True)
                return
            except BackupUnreachable as e:
                print("Backup: could not reach GitHub (%s), try %d of %d" % (e, attempt + 1, BACKUP_START_TRIES), flush=True)
                if attempt + 1 < BACKUP_START_TRIES:
                    time.sleep(min(10, BACKUP_RETRY_SECONDS * (attempt + 1)))
        print("Backup: giving up for now. Exiting instead of starting empty; the host will start the server again.", flush=True)
        sys.exit(1)

    def _restore_once(self):
        status, info = self._json("GET", "/repos/%s" % self.repo)
        if status in (401, 403, 404):
            raise AccessDenied("no access to the repo, HTTP %d" % status)
        if status != 200:
            raise BackupUnreachable("HTTP %d" % status)
        if info.get("private") is not True:
            raise AccessDenied("the repo is PUBLIC, chats must not go there; make it private")
        untrusted = os.path.exists(self.marker)
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0 and not untrusted:
            # Dauerhafte Festplatte oder einfacher Neustart: Die Datei hier ist der neueste Stand
            print("Backup: keeping the existing database %s" % self.path, flush=True)
            self.state = "ok"
            self.may_upload = True
            return
        release = self._release()
        assets = sorted((release or {}).get("assets", []), key=lambda a: a.get("name", ""), reverse=True)
        assets = [a for a in assets if a.get("name", "").startswith("goon-")]
        if not assets:
            print("Backup: no backup saved yet, starting fresh", flush=True)
            self._finish_restore()
            return
        for asset in assets:
            tmp = self.path + ".restoring"
            try:
                raw = gzip.decompress(self._download(asset["id"]))
                with open(tmp, "wb") as f:
                    f.write(raw)
                self._verify(tmp)
            except (OSError, EOFError, sqlite3.Error, ValueError) as e:
                print("Backup: %s is damaged (%s), trying the one before" % (asset.get("name"), type(e).__name__), flush=True)
                if os.path.exists(tmp):
                    os.remove(tmp)
                continue
            for leftover in (self.path + "-wal", self.path + "-shm", self.path + "-journal"):
                if os.path.exists(leftover):
                    os.remove(leftover)
            os.replace(tmp, self.path)
            print("Backup: restored %s (%d KB)" % (asset.get("name"), len(raw) // 1024), flush=True)
            self.last_hash = hashlib.sha256(raw).hexdigest()
            self._finish_restore()
            return
        raise AccessDenied("every saved backup is damaged, look at the release in the repo")

    def _finish_restore(self):
        if os.path.exists(self.marker):
            os.remove(self.marker)
        self.state = "ok"
        self.may_upload = True

    @staticmethod
    def _verify(path):
        db = sqlite3.connect(path)
        try:
            row = db.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                raise ValueError("integrity")
            db.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        finally:
            db.close()

    # ---------- Sichern ----------

    def start(self):
        if self.may_upload:
            threading.Thread(target=self._loop, name="db-backup", daemon=True).start()

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self.upload_now()

    def upload_now(self):
        """Lädt den Stand hoch, wenn er sich geändert hat. Fehler werden beim nächsten Durchlauf wiederholt."""
        if not self.may_upload:
            return False
        with self.lock:
            try:
                raw = self._snapshot()
                digest = hashlib.sha256(raw).hexdigest()
                if digest == self.last_hash:
                    return True
                self._upload(gzip.compress(raw, mtime=0))
                self.last_hash = digest
                self.last_ok = time.time()
                self.state = "ok"
                return True
            except (BackupUnreachable, AccessDenied, sqlite3.Error, OSError) as e:
                self.state = "failing"
                print("Backup: upload failed (%s), trying again later" % type(e).__name__, flush=True)
                return False

    def _snapshot(self):
        """Ein stimmiger Stand der Datenbank, auch während der Server schreibt."""
        tmp = self.path + ".snapshot"
        src = sqlite3.connect(self.path)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        try:
            with open(tmp, "rb") as f:
                return f.read()
        finally:
            os.remove(tmp)

    def _upload(self, data):
        release = self._release()
        if release is None:
            status, release = self._json("POST", "/repos/%s/releases" % self.repo, {
                "tag_name": BACKUP_TAG, "name": "GoonClient backend backup", "prerelease": True,
                "body": "Automatic backups of the GoonClient backend database. Do not delete or make public."})
            if status not in (200, 201):
                # 422 kommt von GitHub, wenn das Repo noch ganz leer ist (es braucht mindestens eine Datei)
                raise BackupUnreachable("cannot create the release, HTTP %d (the repo needs at least one file)" % status)
        name = "goon-%s-%s.sqlite3.gz" % (time.strftime("%Y%m%d-%H%M%S", time.gmtime()), secrets.token_hex(2))
        upload_url = release["upload_url"].split("{")[0] + "?name=" + name
        status, _, _ = self._request("POST", upload_url, data, content_type="application/gzip")
        if status not in (200, 201):
            raise BackupUnreachable("upload HTTP %d" % status)
        # Erst nach dem erfolgreichen Hochladen alte Sicherungen entfernen
        names = {a["name"]: a["id"] for a in release.get("assets", []) if a.get("name", "").startswith("goon-")}
        names[name] = None
        keep = backups_to_keep(names.keys())
        for old, asset_id in names.items():
            if old not in keep and asset_id is not None:
                self._request("DELETE", self.api + "/repos/%s/releases/assets/%s" % (self.repo, asset_id))

    def shutdown(self):
        """Der Hoster beendet den Server (Deploy, Neustart): letzter Stand, damit möglichst nichts fehlt."""
        self.stop_event.set()
        if self.upload_now():
            print("Backup: saved before shutdown", flush=True)

    def health(self):
        return {"state": self.state, "lastUpload": int(self.last_ok)}


class State:
    def __init__(self, args):
        self.args = args
        self.backup = None
        self.store = Store(args.db)
        self.store.chat_ttl = args.chat_ttl
        self.hub = ChatHub()
        self.admin_token = args.admin_token
        # Admin-Konten für Befehle: nur über die Umgebung (ADMIN_UUIDS) oder das Startargument, nie aus dem Client
        self.admin_uuids = set()
        for part in (args.admin_uuids or "").split(","):
            part = part.strip()
            if part:
                try:
                    self.admin_uuids.add(norm_uuid(part))
                except ValueError:
                    print("ADMIN_UUIDS: ignoring invalid uuid %r" % part, flush=True)
        self.adjust_ttl = args.adjust_ttl
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


def clean_admin_message(raw):
    """Nachricht eines Admin-Geschenks: reiner Text, höchstens ADMIN_MESSAGE_MAX Zeichen, keine Steuer- und Formatzeichen."""
    if raw is None or raw == "":
        return ""
    if not isinstance(raw, str):
        raise ValueError("message must be text")
    text = "".join(ch for ch in raw if not (ord(ch) < 32 or ord(ch) == 127 or 0x80 <= ord(ch) < 0xA0 or ch == "\u00a7"))
    text = " ".join(text.split())
    if len(text) > ADMIN_MESSAGE_MAX:
        raise ValueError("message too long (max %d)" % ADMIN_MESSAGE_MAX)
    return text


def admin_target(state, args):
    """Spielername -> UUID, nur bekannte GoonClient-Spieler. Gibt (uuid, name) oder wirft AdminError."""
    name = args.get("player")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", name):
        raise AdminError(400, "bad player name")
    found = state.store.uuids_named(name)
    if not found:
        raise AdminError(404, "player has not used GoonClient")
    if len(found) > 1:
        raise AdminError(409, "several players had this name")
    return found[0], state.store._name(found[0]) or name


def admin_amount(args):
    amount = args.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise AdminError(400, "amount must be a whole number")
    if amount < 1:
        raise AdminError(400, "amount must be at least 1")
    if amount > ADMIN_MAX_AMOUNT:
        raise AdminError(400, "amount too large (max %d)" % ADMIN_MAX_AMOUNT)
    return amount


class AdminError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def cmd_give(state, issuer, issuer_name, args):
    target, target_name = admin_target(state, args)
    amount = admin_amount(args)
    try:
        message = clean_admin_message(args.get("message", ""))
    except ValueError as e:
        raise AdminError(400, str(e))
    check_daily(state, issuer, amount)
    aid = state.store.add_adjustment(target, amount, "give", message, issuer, issuer_name)
    return {"id": aid, "status": "pending", "target": target, "targetName": target_name, "amount": amount, "message": message}


def cmd_del(state, issuer, issuer_name, args):
    target, target_name = admin_target(state, args)
    amount = admin_amount(args)
    check_daily(state, issuer, amount)
    aid = state.store.add_adjustment(target, -amount, "del", "", issuer, issuer_name)
    return {"id": aid, "status": "pending", "target": target, "targetName": target_name, "amount": amount}


def check_daily(state, issuer, amount):
    if state.store.admin_amount_today(issuer) + amount > ADMIN_DAILY_AMOUNT:
        raise AdminError(429, "daily limit reached (max %d per day)" % ADMIN_DAILY_AMOUNT)


# Befehlstabelle: neuer Befehl = eine Funktion (state, issuer, issuer_name, args) -> dict, plus ein Eintrag hier
ADMIN_COMMANDS = {
    "give": cmd_give,
    "del": cmd_del,
}


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
                    codes.append({"code": e["public"], "coins": e["coins"], "eventCoins": e["eventCoins"],
                                  "eventCurrency": e["eventCurrency"], "expires": e["expires"], "usesLeft": left,
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
                    return self.send_json(200, {"ok": True, "backup": state.backup.health() if state.backup else {"state": "off", "lastUpload": 0}})
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
                    uids = list(dict.fromkeys(uids))
                    return self.send_json(200, {"players": state.store.get_many(uids), "active": state.store.active_among(uids)})
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
                if parsed.path.startswith("/v1/chat/"):
                    return self.chat_get(parsed)
                if parsed.path == "/v1/admin/reports":
                    return self.admin_reports(parsed)
                if parsed.path in ("/v1/admin/me", "/v1/admin/history", "/v1/adjustments"):
                    if not self.guard("friends", 240):
                        return
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    if parsed.path == "/v1/admin/me":
                        return self.send_json(200, {"admin": uid in state.admin_uuids})
                    if parsed.path == "/v1/adjustments":
                        state.store.expire_adjustments(state.adjust_ttl)
                        return self.send_json(200, {"adjustments": state.store.adjustments_for(uid)})
                    if uid not in state.admin_uuids:
                        return self.error(403, "not allowed")
                    state.store.expire_adjustments(state.adjust_ttl)
                    return self.send_json(200, {"history": state.store.issuer_history(uid)})
                if parsed.path == "/v1/admin/resets":
                    if not self.admin_ok():
                        return None
                    return self.send_json(200, {"resets": state.store.list_resets(200)})
                if parsed.path == "/v1/account/reset":
                    if not self.guard("friends", 240):
                        return
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    return self.send_json(200, {"reset": state.store.pending_reset(uid)})
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

        # ---------- Chat ----------

        def chat_get(self, parsed):
            is_poll = parsed.path == "/v1/chat/poll"
            if not self.guard("chat_poll" if is_poll else "chat_read", 600):
                return
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            qs = urllib.parse.parse_qs(parsed.query)
            state.store.purge_chat()
            if is_poll:
                wait = min(25.0, max(0.0, float(qs.get("wait", ["25"])[0])))
                result = state.hub.wait(uid, qs.get("boot", [""])[0], int(qs.get("since", ["0"])[0]), wait)
                if result is None:
                    return self.error(503, "busy")
                seq, resync, events = result
                arrived = [e["message"]["id"] for e in events if e.get("type") == "message"]
                for sender, mid in state.store.mark_delivered(uid, arrived):
                    state.hub.publish(sender, {"type": "status", "id": mid, "status": "delivered"})
                try:
                    return self.send_json(200, {"boot": state.hub.boot, "seq": seq, "resync": resync, "events": events})
                except OSError:
                    return None  # der Client ist weg; die Nachrichten holt er beim nächsten Abgleich
            if parsed.path == "/v1/chat/sync":
                boot, seq = state.hub.boot, state.hub.seq
                messages = state.store.take_undelivered(uid)
                for m in messages:
                    state.hub.publish(m["from"], {"type": "status", "id": m["id"], "status": "delivered"})
                return self.send_json(200, {"boot": boot, "seq": seq, "messages": messages})
            if parsed.path == "/v1/chat/state":
                data = state.store.chat_state(uid)
                for f in data["friends"]:
                    f["presence"] = state.hub.presence(f["uuid"])
                return self.send_json(200, data)
            if parsed.path == "/v1/chat/history":
                other = norm_uuid(qs.get("with", [""])[0])
                before = int(qs.get("before", [str(1 << 62)])[0])
                limit = min(50, max(1, int(qs.get("limit", ["30"])[0])))
                return self.send_json(200, {"messages": state.store.history(uid, other, before, limit)})
            return self.error(404, "not found")

        def chat_post(self, parsed, body):
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            state.store.purge_chat()
            path = parsed.path
            if path == "/v1/chat/send":
                other = norm_uuid(body.get("to", ""))
                if not state.store.are_friends(uid, other):
                    return self.error(403, "only friends can chat")
                text, sticker = body.get("text", ""), body.get("sticker", "")
                cid = body.get("cid", "")
                if not isinstance(cid, str) or not CID_RE.fullmatch(cid):
                    return self.error(400, "bad cid")
                if not isinstance(text, str) or not isinstance(sticker, str) or bool(text) == bool(sticker):
                    return self.error(400, "send text or a sticker")
                if sticker and not STICKER_RE.fullmatch(sticker):
                    return self.error(400, "bad sticker id")
                if text:
                    if len(text) > CHAT_MAX_TEXT or not text.strip():
                        return self.error(400, "text too long or empty")
                    if any(ord(ch) < 32 or ord(ch) == 127 or 0x80 <= ord(ch) < 0xA0 or ch == "\u00a7" for ch in text):
                        return self.error(400, "text has control characters")
                    text = text.strip()
                # 5 pro 5 Sekunden und 20 pro Minute je Konto (nicht je Adresse)
                if not state.limiter.allow(uid, "chat_burst", 5, 5.0) or not state.limiter.allow(uid, "chat_minute", 20, 60.0):
                    return self.error(429, "slow down")
                message, fresh = state.store.send_message(uid, other, text, sticker, cid)
                if fresh:
                    state.hub.publish(other, {"type": "message", "message": message})
                return self.send_json(200, message)
            if path == "/v1/chat/read":
                other = norm_uuid(body.get("with", ""))
                upto = body.get("upto", 0)
                if not isinstance(upto, int) or isinstance(upto, bool):
                    return self.error(400, "bad id")
                if state.store.mark_read(uid, other, upto):
                    state.hub.publish(other, {"type": "read", "by": uid, "upto": upto})
                return self.send_json(200, {"ok": True})
            if path == "/v1/chat/delete":
                mid = body.get("id")
                if not isinstance(mid, int) or isinstance(mid, bool):
                    return self.error(400, "bad id")
                other = state.store.delete_message(uid, mid)
                if other is None:
                    return self.error(404, "not your message")
                state.hub.publish(other, {"type": "deleted", "id": mid, "from": uid})
                return self.send_json(200, {"ok": True})
            if path == "/v1/chat/typing":
                other = norm_uuid(body.get("to", ""))
                if state.store.are_friends(uid, other) and state.limiter.allow(uid, "chat_typing", 2, 2.0):
                    state.hub.publish(other, {"type": "typing", "from": uid})
                return self.send_json(200, {"ok": True})
            if path == "/v1/chat/presence":
                mode = body.get("mode")
                if mode not in ("online", "away", "hidden"):
                    return self.error(400, "bad mode")
                state.hub.set_mode(uid, mode)
                return self.send_json(200, {"ok": True})
            if path == "/v1/chat/block":
                other = norm_uuid(body.get("uuid", ""))
                if other == uid:
                    return self.error(400, "that is you")
                blocked = body.get("blocked") is True
                was_friend = state.store.are_friends(uid, other)
                state.store.set_block(uid, other, blocked)
                if blocked and was_friend:
                    state.hub.publish(other, {"type": "friends"})  # für den anderen sieht es aus wie ein Entfernen
                return self.send_json(200, {"blocked": blocked})
            if path == "/v1/chat/report":
                other = norm_uuid(body.get("with", ""))
                mid = body.get("id", 0)
                if not isinstance(mid, int) or isinstance(mid, bool):
                    return self.error(400, "bad id")
                if not state.limiter.allow(uid, "chat_report", 10, 3600.0):
                    return self.error(429, "slow down")
                return self.send_json(200, {"report": state.store.add_report(uid, other, mid)})
            return self.error(404, "not found")

        def admin_command(self):
            """Admin-Befehl aus der Befehlstabelle. Absender nur aus dem Sitzungstoken, nur Konten aus ADMIN_UUIDS."""
            if not self.guard("admin_cmd_ip", 120):
                return None
            try:
                body = self.read_json()
            except (ValueError, json.JSONDecodeError):
                return self.error(400, "bad request")
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            name = body.get("command") if isinstance(body, dict) else None
            if uid not in state.admin_uuids:
                state.store.audit(uid, str(name)[:32], "", {}, "denied: not an admin")
                return self.error(403, "not allowed")
            if not state.limiter.allow(uid, "admin_cmd", ADMIN_COMMANDS_PER_MINUTE, 60.0):
                return self.error(429, "too many admin commands, wait a minute")
            handler = ADMIN_COMMANDS.get(name) if isinstance(name, str) else None
            args = body.get("args", {})
            if handler is None or not isinstance(args, dict):
                return self.error(400, "unknown command")
            issuer_name = state.store._name(uid)
            try:
                result = handler(state, uid, issuer_name, args)
            except AdminError as e:
                state.store.audit(uid, name, str(args.get("player", ""))[:16], {"amount": args.get("amount")}, "rejected: " + e.message)
                return self.error(e.status, e.message)
            state.store.audit(uid, name, result.get("target", ""), {"amount": result.get("amount"), "id": result.get("id"),
                              "message": result.get("message", "")}, "ok")
            return self.send_json(200, result)

        def adjustment_ack(self, path):
            if not self.guard("friends_write", 120):
                return None
            try:
                body = self.read_json()
            except (ValueError, json.JSONDecodeError):
                return self.error(400, "bad request")
            uid = state.uuid_for(self.bearer())
            if uid is None:
                return self.error(401, "not logged in")
            aid = body.get("id") if isinstance(body, dict) else None
            if not isinstance(aid, str) or not ADJ_ID_RE.fullmatch(aid):
                return self.error(400, "bad id")
            if path.endswith("/delivered"):
                status = state.store.mark_adjustment_delivered(uid, aid)
            else:
                amount = body.get("amount")
                if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
                    return self.error(400, "bad amount")
                status = state.store.mark_adjustment_applied(uid, aid, amount)
                if status == "applied":
                    state.store.audit(uid, "applied", uid, {"id": aid, "amount": amount}, "ok")
            if status is None:
                return self.error(404, "no such adjustment")  # auch fremde: nicht verraten, dass es sie gibt
            if status == "bad amount":
                return self.error(400, "bad amount")
            return self.send_json(200, {"status": status})

        def admin_ok(self):
            """Admin-Token prüfen (und bei Fehler schon antworten). Ohne gesetztes GOON_ADMIN_TOKEN gibt es keine Admin-Routen."""
            if not state.admin_token:
                self.error(404, "not found")
                return False
            if not self.guard("admin", 30):
                return False
            if not secrets.compare_digest(self.bearer().encode("utf-8"), state.admin_token.encode("utf-8")):
                self.error(401, "bad token")
                return False
            return True

        def admin_reset(self, parsed, body):
            if parsed.path == "/v1/admin/reset/cancel":
                rid = body.get("id")
                if not isinstance(rid, int) or isinstance(rid, bool):
                    return self.error(400, "bad id")
                if not state.store.cancel_reset(rid):
                    return self.error(404, "no open reset with this id")
                return self.send_json(200, {"ok": True})
            if parsed.path != "/v1/admin/reset":
                return self.error(404, "not found")
            reason = body.get("reason", "")
            if not isinstance(reason, str) or len(reason) > 200:
                return self.error(400, "bad reason")
            raw_uuid, name = body.get("uuid", ""), body.get("name", "")
            if raw_uuid:
                if not isinstance(raw_uuid, str):
                    return self.error(400, "bad uuid")
                uid = norm_uuid(raw_uuid)
            elif isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]{1,16}", name):
                found = state.store.uuids_named(name)
                if not found:
                    return self.error(404, "no GoonClient player with this name has logged in yet; use the uuid")
                if len(found) > 1:
                    return self.error(409, "several players had this name; use the uuid: " + ", ".join(found))
                uid = found[0]
            else:
                return self.error(400, "give exactly one player: uuid or name")
            rid = state.store.add_reset(uid, reason)
            state.hub.publish(uid, {"type": "friends"})  # Client fragt dann bald nach
            return self.send_json(200, {"id": rid, "uuid": uid, "name": state.store._name(uid)})

        def admin_reports(self, parsed):
            """Meldungen ansehen. Ohne gesetztes GOON_ADMIN_TOKEN gibt es diesen Endpunkt nicht."""
            if not state.admin_token:
                return self.error(404, "not found")
            if not self.guard("admin", 30):
                return
            if not secrets.compare_digest(self.bearer().encode("utf-8"), state.admin_token.encode("utf-8")):
                return self.error(401, "bad token")
            limit = min(200, max(1, int(urllib.parse.parse_qs(parsed.query).get("limit", ["50"])[0])))
            return self.send_json(200, {"reports": state.store.list_reports(limit)})

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith("/v1/chat/"):
                if not self.guard("chat_write", 600):
                    return
                try:
                    return self.chat_post(parsed, self.read_json())
                except (ValueError, json.JSONDecodeError, AttributeError):
                    return self.error(400, "bad request")
            is_emote = parsed.path == "/v1/emote"
            is_redeem = parsed.path in ("/v1/redeem", "/v1/redeem/code")
            is_friends = parsed.path.startswith("/v1/friends/")
            is_gift = parsed.path in ("/v1/gifts/send", "/v1/gifts/claim")
            if parsed.path == "/v1/admin/command":
                return self.admin_command()
            if parsed.path in ("/v1/adjustments/delivered", "/v1/adjustments/applied"):
                return self.adjustment_ack(parsed.path)
            if parsed.path.startswith("/v1/admin/"):
                try:
                    body = self.read_json()
                except (ValueError, json.JSONDecodeError):
                    return self.error(400, "bad request")
                if not self.admin_ok():
                    return None
                try:
                    return self.admin_reset(parsed, body)
                except (ValueError, AttributeError):
                    return self.error(400, "bad request")
            group, limit = ("emote", 60) if is_emote else ("redeem", 20) if is_redeem \
                else ("friends_write", 60) if is_friends else ("gifts", 120) if is_gift else ("auth", 30)
            if not self.guard(group, limit):
                return
            try:
                body = self.read_json()  # immer lesen, sonst bleiben Bytes auf der Verbindung liegen
                if parsed.path == "/v1/account/reset/ack":
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    rid = body.get("id")
                    if not isinstance(rid, int) or isinstance(rid, bool):
                        return self.error(400, "bad id")
                    return self.send_json(200, {"ok": state.store.ack_reset(uid, rid)})
                if is_friends:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    other = norm_uuid(body.get("uuid", ""))
                    if other == uid:
                        return self.error(400, "that is you")
                    if parsed.path == "/v1/friends/request":
                        if not state.store.are_friends(uid, other) and not state.limiter.allow(uid, "friend_requests", MAX_REQUESTS_PER_DAY, 86400.0):
                            return self.error(429, "too many friend requests today")
                        status = state.store.request_friend(uid, other)
                        if status == "blocked":
                            return self.error(409, "you blocked this player")
                        if status == "full":
                            return self.error(409, "friend list is full")
                        state.hub.publish(other, {"type": "friends"})
                        return self.send_json(200, {"status": status})
                    if parsed.path == "/v1/friends/respond":
                        status = state.store.respond_friend(uid, other, body.get("accept") is True)
                        if status is None:
                            return self.error(404, "no such friend request")
                        if status == "full":
                            return self.error(409, "friend list is full")
                        state.hub.publish(other, {"type": "friends"})
                        return self.send_json(200, {"status": status})
                    if parsed.path == "/v1/friends/remove":
                        state.store.remove_friend(uid, other)
                        state.hub.publish(other, {"type": "friends"})
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
                    if entry["item"] and body.get("items") is not True:
                        return self.error(426, "update GoonClient to redeem this code")
                    if entry["eventCoins"] and body.get("eventCoins") is not True:
                        return self.error(426, "update GoonClient to redeem this code")
                    if entry["maxUses"] is not None and state.store.claim_count(entry["id"]) >= entry["maxUses"]:
                        return self.error(410, "code used up")
                    if not state.store.claim(uid, entry["id"]):
                        return self.error(409, "already redeemed")
                    reply = {"ok": True, "id": entry["id"], "coins": entry["coins"]}
                    if entry["item"]:
                        reply["item"] = entry["item"]
                    if entry["eventCoins"]:
                        reply["eventCoins"] = entry["eventCoins"]
                        reply["eventCurrency"] = entry["eventCurrency"]
                    return self.send_json(200, reply)
                if is_redeem:
                    uid = state.uuid_for(self.bearer())
                    if uid is None:
                        return self.error(401, "not logged in")
                    code = body.get("id")
                    if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]{1,32}", code):
                        return self.error(400, "bad code id")
                    known = state.codes.find_id(code)
                    if known is not None and code_expired(known):
                        return self.error(410, "code expired")
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
    p.add_argument("--chat-ttl", type=float, default=float(os.environ.get("GOON_CHAT_TTL", CHAT_TTL_DEFAULT)),
                   help="Chat-Nachrichten nach so vielen Sekunden löschen (Standard: 7 Tage)")
    p.add_argument("--admin-uuids", default=os.environ.get("ADMIN_UUIDS", ""),
                   help="Minecraft-UUIDs der GoonClient-Admins, durch Kommas getrennt (Standard: Umgebungsvariable ADMIN_UUIDS)")
    p.add_argument("--adjust-ttl", type=float, default=float(os.environ.get("GOON_ADJUST_TTL", ADJUST_TTL_DEFAULT)),
                   help="Offene Admin-Anpassungen nach so vielen Sekunden verfallen lassen (Standard: 30 Tage)")
    p.add_argument("--admin-token", default=os.environ.get("GOON_ADMIN_TOKEN", ""),
                   help="Token für /v1/admin/reports (Standard: Umgebungsvariable GOON_ADMIN_TOKEN; leer = kein Abruf)")
    p.add_argument("--backup-seconds", type=float, default=float(os.environ.get("GOON_BACKUP_SECONDS", BACKUP_INTERVAL_DEFAULT)),
                   help="So oft die Datenbank sichern, wenn sie sich geändert hat (Standard: alle 2 Minuten)")
    args = p.parse_args()
    if os.environ.get("RENDER") and not args.trust_proxy:
        # Auf Render kommen alle Anfragen über deren Proxy: ohne X-Forwarded-For teilen sich ALLE Spieler ein Limit
        # (dann bekommt bei mehreren Spielern jeder "too many requests" und Emotes/Accessoires kommen nicht an)
        args.trust_proxy = True
    # Das Token kommt nur aus der Umgebung: auf der Kommandozeile stünde es in Prozesslisten und Logs
    backup = DbBackup(args.db, os.environ.get("GOON_BACKUP_REPO", "").strip(), os.environ.get("GOON_BACKUP_TOKEN", "").strip(),
                      os.environ.get("GOON_BACKUP_API", "https://api.github.com"), args.backup_seconds)
    backup.restore()  # vor dem Öffnen der Datenbank
    state = State(args)
    state.backup = backup
    backup.start()
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    httpd.daemon_threads = True

    def stop(signum, frame):
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, stop)  # das Gegenstück unter Windows
    print("GoonClient backend on http://%s:%d%s" % (args.host, args.port, "  (INSECURE test mode)" if args.insecure else ""))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    backup.shutdown()


if __name__ == "__main__":
    main()
