#!/usr/bin/env python3
"""
Setzt die GoonClient-Daten EINES Spielers zurück (z.B. wenn er über ein geteiltes Modpack fremde Coins/Cosmetics bekommen hat).
Betrifft immer nur den einen genannten Spieler. Auf dem Server werden sofort seine angezeigten Cosmetics, Stats und offenen
Freundschaftsanfragen gelöscht; im Spiel räumt sein Client die Daten beim nächsten Start beiseite (nach "foreign/", nicht gelöscht).

Braucht das Admin-Token des Servers (auf Render: Umgebungsvariable GOON_ADMIN_TOKEN). Hier als Umgebungsvariable setzen:
    set GOON_ADMIN_TOKEN=...            (Windows, cmd)
    $env:GOON_ADMIN_TOKEN="..."         (PowerShell)

Benutzung:
    py -3 tools/backend/admin_reset.py SpielerName [--reason "geteiltes Modpack"]
    py -3 tools/backend/admin_reset.py 069a79f4-44e9-4726-a5be-fca90e38aaf5
    py -3 tools/backend/admin_reset.py --list
    py -3 tools/backend/admin_reset.py --cancel 3
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://goonclient-backend-1.onrender.com"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")


def call(url, token, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("User-Agent", "GoonClient-Admin")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def main(argv=None):
    p = argparse.ArgumentParser(description="GoonClient-Daten EINES Spielers zurücksetzen")
    p.add_argument("player", nargs="?", help="Minecraft-Name oder UUID des Spielers")
    p.add_argument("--reason", default="shared modpack", help="Grund (nur zur Übersicht)")
    p.add_argument("--list", action="store_true", help="alle Resets anzeigen")
    p.add_argument("--cancel", type=int, help="offenen Reset mit dieser Id zurücknehmen")
    p.add_argument("--url", default=os.environ.get("GOON_BACKEND_URL", DEFAULT_URL))
    p.add_argument("--yes", action="store_true", help="ohne Rückfrage")
    a = p.parse_args(argv)
    token = os.environ.get("GOON_ADMIN_TOKEN", "")
    if not token:
        print("GOON_ADMIN_TOKEN ist nicht gesetzt (dasselbe Token wie auf dem Server).")
        return 2
    if a.list:
        status, r = call(a.url, token, "GET", "/v1/admin/resets")
        if status != 200:
            print("Fehler %d: %s" % (status, r.get("error", r)))
            return 1
        for x in r.get("resets", []):
            print("#%-4d %-9s %-16s %s  (%s)" % (x["id"], x["state"], x["name"] or "?", x["uuid"], x["reason"]))
        if not r.get("resets"):
            print("Noch keine Resets.")
        return 0
    if a.cancel is not None:
        status, r = call(a.url, token, "POST", "/v1/admin/reset/cancel", {"id": a.cancel})
        print("Zurückgenommen." if status == 200 else "Fehler %d: %s" % (status, r.get("error", r)))
        return 0 if status == 200 else 1
    if not a.player:
        p.print_help()
        return 2
    player = a.player.strip()
    if UUID_RE.match(player):
        body = {"uuid": player}
    elif NAME_RE.match(player):
        body = {"name": player}
    else:
        print("Das ist weder ein Minecraft-Name noch eine UUID: %s" % player)
        return 2
    if not a.yes:
        answer = input("GoonClient-Daten von '%s' zurücksetzen? Nur dieser eine Spieler ist betroffen. [j/N] " % player)
        if answer.strip().lower() not in ("j", "ja", "y", "yes"):
            print("Abgebrochen.")
            return 1
    body["reason"] = a.reason[:200]
    status, r = call(a.url, token, "POST", "/v1/admin/reset", body)
    if status != 200:
        print("Fehler %d: %s" % (status, r.get("error", r)))
        return 1
    print("Reset #%d für %s (%s) angelegt. Sein Client räumt die Daten beim nächsten Start mit GoonClient 3.98.0+ beiseite."
          % (r["id"], r.get("name") or player, r["uuid"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
