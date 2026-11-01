#!/usr/bin/env python3
"""
End-to-End-Test für server.py (nur Standardbibliothek): startet das Backend im --insecure-Testmodus auf einem freien Port
und prüft Cosmetics (inkl. Hut/Flügel/Accessoire), Codes, Freundschaftsanfragen, Stats und den Freundes-Schutz.
    python tools/backend/test_backend.py
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"
C = "33333333-3333-3333-3333-333333333333"
failures = 0


def check(ok, what):
    global failures
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        failures += 1


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Client:
    def __init__(self, base):
        self.base = base
        self.token = None

    def req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        if self.token:
            r.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def login(self, name, uid):
        _, ch = self.req("POST", "/v1/auth/challenge", {})
        status, res = self.req("POST", "/v1/auth/verify", {"username": name, "serverId": ch["serverId"], "uuid": uid})
        self.token = res.get("token")
        return status


def main():
    port = free_port()
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "test.db")
    codes = os.path.join(tmp, "codes.json")
    with open(os.path.join(HERE, "codes.json"), encoding="utf-8") as f:
        real_codes = json.load(f)
    # Ein Code mit falschem Klartext darf nie auf der Website erscheinen
    real_codes["codes"].append({"id": "fakepublic", "hash": "0" * 64, "coins": 5, "public": True, "code": "GOON-FAKE-0000"})
    with open(codes, "w", encoding="utf-8") as f:
        json.dump(real_codes, f)
    # Test-Website: zwei JARs (die neuere muss gewinnen, auch bei 3.10 > 3.9) und ein Changelog
    site = os.path.join(tmp, "site")
    os.makedirs(os.path.join(site, "downloads"))
    with open(os.path.join(site, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><title>GoonClient</title>")
    for v in ("3.9.0", "3.10.0"):
        with open(os.path.join(site, "downloads", "goonclient-%s.jar" % v), "wb") as f:
            f.write(b"JAR-" + v.encode())
    with open(os.path.join(site, "downloads", "goonclient-3.10.0.jar.sig"), "w", encoding="ascii") as f:
        f.write("A" * 86 + "==\n")
    with open(os.path.join(site, "downloads", "goonclient-3.10.0-sources.jar"), "wb") as f:
        f.write(b"SOURCES")
    with open(os.path.join(site, "CHANGELOG.md"), "w", encoding="utf-8") as f:
        f.write("# GoonClient\n\n| Minecraft | 1.21.11 |\n|---|---|\n| Fabric API | 0.141.5+1.21.11 |\n\n## 1. Setup\nx\n\n"
                "## Update 3.10.0: Neu\n- Punkt A\n\n## Update 3.9.0: Alt\n- Punkt B\n\n## 2. Sonstiges\ny\n")
    events = os.path.join(tmp, "events.json")
    with open(os.path.join(HERE, "events.json"), encoding="utf-8") as f:
        real_events = json.load(f)
    real_events["events"] += [
        {"id": "BAD ID", "name": "x", "currency": "y", "currencyName": "z", "start": "2026-01-01T00:00:00+01:00",
         "end": "2026-01-02T00:00:00+01:00", "items": ["cape.lantern"]},
        {"id": "notz", "name": "x", "currency": "y", "currencyName": "z", "start": "2026-01-01T00:00:00",
         "end": "2026-01-02T00:00:00", "items": ["cape.lantern"]},
        {"id": "toolong", "name": "x", "currency": "y", "currencyName": "z", "start": "2026-01-01T00:00:00+01:00",
         "end": "2027-01-02T00:00:00+01:00", "items": ["cape.lantern"]}]
    with open(events, "w", encoding="utf-8") as f:
        json.dump(real_events, f)
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "server.py"), "--port", str(port), "--db", db, "--insecure",
                             "--codes", codes, "--site", site, "--events", events],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/v1/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        a, b, c = Client(base), Client(base), Client(base)
        check(a.login("Alice", A) == 200 and b.login("Bob", B) == 200 and c.login("Carl", C) == 200, "three logins")

        # Events (events.json): ohne Anmeldung, ungültige Einträge fallen weg, Zeiten mit Zeitzone
        s, ev = Client(base).req("GET", "/v1/events")
        lst = ev.get("events", [])
        check(s == 200 and len(lst) == 1 and lst[0]["id"] == "halloween2026", "events: only valid entries: %r" % [e.get("id") for e in lst])
        check(lst and lst[0]["startMs"] == 1793401200000 and lst[0]["endMs"] == 1794006000000, "events: times in ms (German time)")
        check(lst and len(lst[0]["items"]) == 15 and lst[0]["currency"] == "halloween" and lst[0]["theme"] == "halloween", "events: fields")
        real_events["events"].append({"id": "winter2026", "name": "Winter", "currency": "snow", "currencyName": "Snowflakes",
                                      "start": "2026-12-20T00:00:00+01:00", "end": "2027-01-03T00:00:00+01:00",
                                      "color": "#60A5FA", "theme": "winter", "items": ["cape.lantern"]})
        with open(events, "w", encoding="utf-8") as f:
            json.dump(real_events, f)
        time.sleep(0.05)
        os.utime(events, None)
        ids = [e["id"] for e in Client(base).req("GET", "/v1/events")[1].get("events", [])]
        check(ids == ["halloween2026", "winter2026"], "events: new event at once (hot reload): %r" % ids)

        # Schrift: Rundlauf, ungültige Ids werden verworfen, alte Einträge ohne "font" bleiben gültig
        a.req("PUT", "/v1/cosmetics", {"cape": "gold", "font": "royal"})
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A)
        check(got["players"][A].get("font") == "royal", "font round trip")
        a.req("PUT", "/v1/cosmetics", {"cape": "gold", "font": "Bad-Font!"})
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A)
        check(got["players"][A].get("font") == "", "invalid font id dropped")
        a.req("PUT", "/v1/cosmetics", {"cape": "gold", "font": "x" * 25})
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A)
        check(got["players"][A].get("font") == "", "too long font id dropped")
        a.req("PUT", "/v1/cosmetics", {"cape": "gold"})
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A)
        check(got["players"][A].get("font") == "" and got["players"][A].get("cape") == "gold", "old client without font stays valid")
        # Cosmetics mit 3D-Accessoires
        s, _ = a.req("PUT", "/v1/cosmetics", {"cape": "gold", "badge": "star", "hat": "crown", "wings": "angel",
                                               "accessory": "halo", "evil": "x", "tag": "BAD ID!"})
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A)
        p = got["players"].get(A, {})
        check(s == 200 and p.get("hat") == "crown" and p.get("wings") == "angel" and p.get("accessory") == "halo", "accessories stored")
        check("evil" not in p and p.get("tag") == "", "unknown fields dropped, bad ids cleared")
        nobody = "00000000-0000-4000-8000-000000000001"
        _, got = b.req("GET", "/v1/cosmetics?uuids=" + A + "," + nobody)
        check(got.get("active") == [A], "active lists only players who uploaded recently")

        # Codes: einmal pro Account
        check(a.req("POST", "/v1/redeem", {"id": "launch100"})[0] == 200, "redeem first time")
        check(a.req("POST", "/v1/redeem", {"id": "launch100"})[0] == 409, "redeem twice refused")
        check(b.req("POST", "/v1/redeem", {"id": "launch100"})[0] == 200, "other account can redeem")

        # Codes über das Backend prüfen (codes.json), ohne neue Client-Version
        s, r = c.req("POST", "/v1/redeem/code", {"code": " goon-3pcm ypjy "})
        check(s == 200 and r.get("id") == "bonus3000" and r.get("coins") == 3000, "server checks typed code (3000)")
        check(c.req("POST", "/v1/redeem/code", {"code": "GOON-3PCM-YPJY"})[0] == 409, "server code only once per account")
        check(c.req("POST", "/v1/redeem/code", {"code": "GOON-NOPE-NOPE"})[0] == 400, "wrong code rejected")
        check(c.req("POST", "/v1/redeem/code", {"code": 12345})[0] == 400, "non-text code rejected")
        check(Client(base).req("POST", "/v1/redeem/code", {"code": "GOON-3PCM-YPJY"})[0] == 401, "code needs login")
        check(c.req("POST", "/v1/redeem/code", {"code": "GOON-9GAT-ZTY7"})[0] == 200, "launch code also via server")
        check(a.req("POST", "/v1/redeem/code", {"code": "GOON-9GAT-ZTY7"})[0] == 409, "old-path claim counts for new path too")
        # Neuen Code mit add_code.py anlegen: gilt sofort, ohne Neustart; Limit und Ablaufdatum
        out = subprocess.run([sys.executable, os.path.join(HERE, "add_code.py"), "777", "--code", "GOON-TEST-7777",
                              "--max-uses", "2", "--file", codes], capture_output=True, text=True)
        subprocess.run([sys.executable, os.path.join(HERE, "add_code.py"), "50", "--code", "GOON-OLD-0001",
                        "--expires", "2020-01-01", "--file", codes], capture_output=True, text=True)
        time.sleep(0.05)
        os.utime(codes, None)
        s, r = a.req("POST", "/v1/redeem/code", {"code": "goon-test-7777"})
        check(out.returncode == 0 and s == 200 and r.get("coins") == 777, "new code works at once (hot reload)")
        check(b.req("POST", "/v1/redeem/code", {"code": "goon-test-7777"})[0] == 200, "second player within max uses")
        s, r = c.req("POST", "/v1/redeem/code", {"code": "goon-test-7777"})
        check(s == 410 and "used up" in r.get("error", ""), "max uses reached -> 410")
        s, r = a.req("POST", "/v1/redeem/code", {"code": "GOON-OLD-0001"})
        check(s == 410 and "expired" in r.get("error", ""), "expired code -> 410")
        # Code für ein exklusives Item (ohne Coins): alte Clients bekommen 426 und verbrauchen den Code nicht
        out = subprocess.run([sys.executable, os.path.join(HERE, "add_code.py"), "0", "--item", "accessory.hackerorbit",
                              "--code", "GOON-ITEM-0001", "--file", codes], capture_output=True, text=True)
        time.sleep(0.05)
        os.utime(codes, None)
        check(out.returncode == 0, "item code created: " + out.stderr)
        check(a.req("POST", "/v1/redeem/code", {"code": "GOON-ITEM-0001"})[0] == 426, "item code refused for old clients")
        s, r = a.req("POST", "/v1/redeem/code", {"code": "GOON-ITEM-0001", "items": True})
        check(s == 200 and r.get("item") == "accessory.hackerorbit" and r.get("coins") == 0, "item code gives the item: %r" % (r,))
        check(a.req("POST", "/v1/redeem/code", {"code": "GOON-ITEM-0001", "items": True})[0] == 409, "item code only once")
        bad = subprocess.run([sys.executable, os.path.join(HERE, "add_code.py"), "0", "--file", codes], capture_output=True, text=True)
        check(bad.returncode != 0, "0 coins without item refused")
        listed = subprocess.run([sys.executable, os.path.join(HERE, "add_code.py"), "--list", "--file", codes],
                                capture_output=True, text=True).stdout
        check("bonus3000" in listed and "GOON-TEST-7777" not in listed and "GOON-TEST-7777" not in open(codes).read(),
              "codes.json stores only hashes")

        # Stats hochladen
        s, _ = a.req("PUT", "/v1/stats", {"coins": 4321, "earned": 9000, "playSeconds": 3600,
                                           "owned": ["cape.gold", "hat.crown", "BAD", "cape.gold"]})
        check(s == 200, "stats upload")

        # Ohne Freundschaft keine Stats
        check(b.req("GET", "/v1/friends/profile?uuid=" + A)[0] == 403, "stats hidden from non-friends")

        # Anfrage A -> B
        s, r = a.req("POST", "/v1/friends/request", {"uuid": B})
        check(s == 200 and r.get("status") == "sent", "request sent")
        _, ov = b.req("GET", "/v1/friends")
        check([x["uuid"] for x in ov["incoming"]] == [A] and ov["incoming"][0]["name"] == "Alice", "B sees incoming request with name")
        _, ova = a.req("GET", "/v1/friends")
        check([x["uuid"] for x in ova["outgoing"]] == [B] and ova["friends"] == [], "A sees outgoing request")
        check(a.req("POST", "/v1/friends/request", {"uuid": A})[0] == 400, "cannot befriend yourself")
        check(c.req("POST", "/v1/friends/respond", {"uuid": A, "accept": True})[0] == 404, "cannot accept a request meant for someone else")

        # B nimmt an
        s, r = b.req("POST", "/v1/friends/respond", {"uuid": A, "accept": True})
        check(s == 200 and r.get("status") == "friends", "B accepts")
        _, ov = b.req("GET", "/v1/friends")
        _, ova = a.req("GET", "/v1/friends")
        check(ov["incoming"] == [] and [x["uuid"] for x in ov["friends"]] == [A], "B: request gone, A is friend")
        check([x["uuid"] for x in ova["friends"]] == [B] and ova["outgoing"] == [] and ova["friends"][0]["name"] == "Bob",
              "A: B is friend with name")

        # Stats jetzt sichtbar
        s, prof = b.req("GET", "/v1/friends/profile?uuid=" + A)
        st = prof.get("stats") or {}
        check(s == 200 and st.get("coins") == 4321 and st.get("owned") == ["cape.gold", "hat.crown"], "friend sees stats (cleaned)")
        check((prof.get("cosmetics") or {}).get("cape") == "gold" and prof.get("name") == "Alice", "friend sees cosmetics and name")
        s, prof = a.req("GET", "/v1/friends/profile?uuid=" + B)
        check(s == 200 and prof.get("stats") is None, "friend without stats upload gives stats null")
        check(c.req("GET", "/v1/friends/profile?uuid=" + A)[0] == 403, "third player still blocked")

        # Gegenseitige Anfrage = sofort Freunde; Ablehnen
        c.req("POST", "/v1/friends/request", {"uuid": A})
        s, r = a.req("POST", "/v1/friends/request", {"uuid": C})
        check(r.get("status") == "friends", "mutual request makes friends at once")
        a.req("POST", "/v1/friends/remove", {"uuid": C})
        c.req("POST", "/v1/friends/request", {"uuid": B})
        s, r = b.req("POST", "/v1/friends/respond", {"uuid": C, "accept": False})
        _, ovc = c.req("GET", "/v1/friends")
        check(r.get("status") == "declined" and ovc["outgoing"] == [] and ovc["friends"] == [], "decline removes the request")
        _, ova = a.req("GET", "/v1/friends")
        check([x["uuid"] for x in ova["friends"]] == [B], "remove ends friendship")

        # Geschenke (A und B sind Freunde, C nicht)
        gid = "a1b2c3d4e5f60718293a4b5c"
        s, r = a.req("POST", "/v1/gifts/send", {"id": gid, "to": B, "coins": 500, "item": ""})
        check(s == 200 and r.get("status") == "pending", "gift sent to friend")
        check(a.req("POST", "/v1/gifts/send", {"id": gid, "to": B, "coins": 500, "item": ""})[1].get("status") == "pending",
              "resending the same gift is harmless")
        check(c.req("POST", "/v1/gifts/send", {"id": gid, "to": A, "coins": 5, "item": ""})[0] == 403, "no gifts to non-friends")
        check(b.req("POST", "/v1/gifts/send", {"id": gid, "to": A, "coins": 5, "item": ""})[0] == 409, "foreign gift id refused")
        check(a.req("POST", "/v1/gifts/send", {"id": "f" * 24, "to": B, "coins": 5, "item": "cape.gold"})[0] == 400, "coins and item at once refused")
        check(a.req("POST", "/v1/gifts/send", {"id": "e" * 24, "to": B, "coins": 99999, "item": ""})[0] == 400, "too many coins refused")
        check(a.req("POST", "/v1/gifts/send", {"id": "d" * 24, "to": A, "coins": 5, "item": ""})[0] == 400, "no gift to yourself")
        s, r = a.req("POST", "/v1/gifts/send", {"id": "c" * 24, "to": B, "coins": 0, "item": "cape.gold"})
        _, gb = b.req("GET", "/v1/gifts")
        inc = {g["id"]: g for g in gb.get("incoming", [])}
        check(s == 200 and set(inc) == {gid, "c" * 24} and inc[gid]["coins"] == 500 and inc[gid]["fromName"] == "Alice"
              and inc["c" * 24]["item"] == "cape.gold", "friend sees incoming gifts")
        check(c.req("POST", "/v1/gifts/claim", {"id": gid})[0] == 404, "only the receiver can claim")
        check(b.req("POST", "/v1/gifts/claim", {"id": gid})[0] == 200 and b.req("POST", "/v1/gifts/claim", {"id": gid})[0] == 200,
              "claim (twice is harmless)")
        _, ga = a.req("GET", "/v1/gifts")
        _, gb = b.req("GET", "/v1/gifts")
        check(ga["sent"].get(gid) is True and ga["sent"].get("c" * 24) is False, "sender sees which gifts were claimed")
        check([g["id"] for g in gb["incoming"]] == ["c" * 24], "claimed gift no longer incoming")
        check(a.req("POST", "/v1/gifts/send", {"id": gid, "to": B, "coins": 500, "item": ""})[1].get("status") == "claimed",
              "resend after claim reports claimed")
        check(Client(base).req("GET", "/v1/gifts")[0] == 401, "gifts need login")

        # Ohne Login
        anon = Client(base)
        check(anon.req("GET", "/v1/friends")[0] == 401 and anon.req("POST", "/v1/friends/request", {"uuid": B})[0] == 401,
              "friends need login")

        # Emotes von Spieler zu Spieler: A startet, B und C sehen es (mit laufender Nummer und Alter)
        s, r = a.req("POST", "/v1/emote", {"id": "levitate"})
        check(s == 200 and r.get("seq", 0) > 0, "emote sent")
        _, got = b.req("GET", "/v1/emotes?uuids=%s,%s" % (A, C))
        e = got["players"].get(A, {})
        check(e.get("id") == "levitate" and e.get("seq") == r["seq"] and 0 <= e.get("ageMs", -1) < 2000 and C not in got["players"],
              "other player sees the emote")
        check(a.req("POST", "/v1/emote", {"id": "nope"})[0] == 400, "unknown emote rejected")
        check(anon.req("POST", "/v1/emote", {"id": "wave"})[0] == 401, "emote needs login")
        # Accessoires wechseln: der neue Stand kommt beim anderen an
        a.req("PUT", "/v1/cosmetics", {"hat": "tophat", "wings": "", "accessory": "backpack"})
        _, got = c.req("GET", "/v1/cosmetics?uuids=" + A)
        p = got["players"].get(A, {})
        check(p.get("hat") == "tophat" and p.get("wings") == "" and p.get("accessory") == "backpack", "changed accessories arrive")

        # Website: Seite, Download der neuesten JAR, Daten mit Updates und öffentlichen Codes
        page = urllib.request.urlopen(base + "/", timeout=5)
        check(page.status == 200 and "text/html" in page.headers.get("Content-Type", "") and b"GoonClient" in page.read(), "website served")
        dl = urllib.request.urlopen(base + "/download", timeout=5)
        check(dl.read() == b"JAR-3.10.0" and "goonclient-3.10.0.jar" in dl.headers.get("Content-Disposition", ""),
              "download = newest jar (3.10.0 > 3.9.0, no sources jar)")
        _, s = anon.req("GET", "/v1/site")
        check(s.get("version") == "3.10.0" and [u["version"] for u in s.get("updates", [])] == ["3.10.0", "3.9.0"]
              and s["updates"][0]["title"] == "Neu" and "Punkt A" in s["updates"][0]["body"] and "Setup" not in s["updates"][1]["body"],
              "site data: version and changelog sections")
        check(s.get("info", {}).get("minecraft") == "1.21.11" and s["info"].get("fabricApi") == "0.141.5+1.21.11", "site info from table")
        shown = [c["code"] for c in s.get("codes", [])]
        check("GOON-HOURLY-1000" in shown and "GOON-9GAT-ZTY7" in shown and "GOON-FAKE-0000" not in shown
              and "GOON-TEST-7777" not in shown, "public codes shown, fake/non-public hidden: %s" % shown)
        check(all(c["coins"] > 0 for c in s["codes"]), "codes with coins")
        # Eingebauter Updater: Version, Prüfsumme, Signatur, genau diese Datei
        _, u = anon.req("GET", "/v1/update")
        check(u.get("version") == "3.10.0" and u.get("file") == "goonclient-3.10.0.jar" and u.get("size") == len(b"JAR-3.10.0")
              and u.get("sha256") == hashlib.sha256(b"JAR-3.10.0").hexdigest() and u.get("signature") == "A" * 86 + "=="
              and u.get("minecraft") == "1.21.11" and u.get("title") == "Neu" and "Punkt A" in u.get("notes", "")
              and u.get("url") == "/download/goonclient-3.10.0.jar", "update info: %s" % u)
        check(urllib.request.urlopen(base + "/download/goonclient-3.9.0.jar", timeout=5).read() == b"JAR-3.9.0", "download exact file")
        for bad in ("/download/..%2Fserver.py", "/download/goonclient-3.10.0-sources.jar", "/download/goonclient-3.10.0.jar.sig",
                    "/download/x.jar"):
            try:
                code = urllib.request.urlopen(base + bad, timeout=5).status
            except urllib.error.HTTPError as err:
                code = err.code
            check(code == 404, "only real client jars downloadable: %s -> %s" % (bad, code))
        ref = urllib.request.Request(base + "/download", method="HEAD")
        check(urllib.request.urlopen(ref, timeout=5).status == 200, "HEAD works")
    finally:
        proc.terminate()
        proc.wait(5)

    # Render: alle Anfragen kommen über den Proxy. Jeder Spieler (X-Forwarded-For) muss sein eigenes Limit haben
    port2 = free_port()
    env = dict(os.environ, RENDER="true", PORT=str(port2))
    proc2 = subprocess.Popen([sys.executable, os.path.join(HERE, "server.py"), "--db", os.path.join(tmp, "r.db"), "--insecure",
                              "--codes", codes], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base2 = "http://127.0.0.1:%d" % port2
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base2 + "/v1/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

        def challenge(ip):
            r = urllib.request.Request(base2 + "/v1/auth/challenge", data=b"{}", method="POST")
            r.add_header("Content-Type", "application/json")
            r.add_header("X-Forwarded-For", ip + ", 10.0.0.1")
            try:
                return urllib.request.urlopen(r, timeout=5).status
            except urllib.error.HTTPError as err:
                return err.code

        first = [challenge("1.1.1.1") for _ in range(30)]
        check(all(x == 200 for x in first) and challenge("1.1.1.1") == 429, "render: one player hits his own limit")
        check(challenge("2.2.2.2") == 200, "render: other players are not blocked by him (own limit per player)")
    finally:
        proc2.terminate()
        proc2.wait(5)
    print("%s, %d failed" % ("ALL OK" if failures == 0 else "FAILURES", failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
