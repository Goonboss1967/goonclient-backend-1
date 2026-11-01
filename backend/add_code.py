#!/usr/bin/env python3
"""
Legt einen neuen Goon-Coins-Code in codes.json an (nur Python-Standardbibliothek). Danach codes.json auf GitHub
hochladen bzw. ersetzen; Render deployt neu und der Code gilt sofort für alle Spieler, ohne neue Client-Version.

  py -3 tools/backend/add_code.py 500                          zufälliger Code für 500 Coins
  py -3 tools/backend/add_code.py 500 --code GOON-WELCOME-1    eigener Code
  py -3 tools/backend/add_code.py 1000 --max-uses 20           nur die ersten 20 Spieler
  py -3 tools/backend/add_code.py 250 --expires 2026-12-31     gültig bis einschließlich 31.12.2026
  py -3 tools/backend/add_code.py 500 --public                 Code wird auf der Website angezeigt
  py -3 tools/backend/add_code.py 0 --item accessory.hackerorbit   Code für ein exklusives Item (ohne Coins)
    Items per Code sind immer exklusiv: das Item muss im Client als exclusive(...) in ShopCatalog stehen.
  py -3 tools/backend/add_code.py --list                       alle Codes anzeigen (nur Ids, der Klartext ist nicht gespeichert)

In codes.json steht nur der Hash. Den ausgegebenen Code selbst gut aufheben, er lässt sich nicht wiederherstellen.
Ausnahme: mit --public steht der Code zusätzlich im Klartext drin, damit die Website ihn zeigen kann.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SALT = "goonclient-code-v1|"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize(text):
    return "".join(ch for ch in text.upper() if ("A" <= ch <= "Z") or ("0" <= ch <= "9"))


def main():
    p = argparse.ArgumentParser(description="Neuen Goon-Coins-Code anlegen")
    p.add_argument("coins", type=int, nargs="?", help="Anzahl Goon Coins (0-100000, 0 nur zusammen mit --item)")
    p.add_argument("--item", help="exklusives Item, das der Code zusätzlich gibt (Shop-Id, z.B. accessory.hackerorbit)")
    p.add_argument("--code", help="eigener Code statt eines zufälligen")
    p.add_argument("--id", help="Name des Codes in der Datei (Standard: automatisch)")
    p.add_argument("--max-uses", type=int, help="höchstens so viele Spieler insgesamt")
    p.add_argument("--expires", help="letzter gültiger Tag, JJJJ-MM-TT")
    p.add_argument("--public", action="store_true",
                   help="Code auf der Website anzeigen (dann steht der Klartext in codes.json)")
    p.add_argument("--file", default=os.path.join(HERE, "codes.json"))
    p.add_argument("--list", action="store_true", help="vorhandene Codes anzeigen")
    a = p.parse_args()

    data = {"codes": []}
    if os.path.exists(a.file):
        with open(a.file, encoding="utf-8") as f:
            data = json.load(f)
    codes = data.setdefault("codes", [])

    if a.list:
        for c in codes:
            extra = []
            if c.get("maxUses"):
                extra.append("max %d" % c["maxUses"])
            if c.get("expires"):
                extra.append("bis %s" % c["expires"])
            if c.get("item"):
                extra.append("Item %s" % c["item"])
            print("%-20s %6d Coins  %s" % (c["id"], c.get("coins", 0), ", ".join(extra)))
        return
    if a.item and not re.fullmatch(r"[a-z]{1,16}\.[a-z0-9_]{1,32}", a.item):
        sys.exit("--item bitte als Shop-Id angeben, z.B. accessory.hackerorbit.")
    if a.coins is None or not (0 if a.item else 1) <= a.coins <= 100000:
        sys.exit("Bitte eine Coin-Anzahl zwischen 1 und 100000 angeben (z.B. add_code.py 500); 0 nur mit --item.")
    if a.expires and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.expires):
        sys.exit("--expires bitte als JJJJ-MM-TT angeben.")

    code = a.code or "GOON-" + "".join(secrets.choice(ALPHABET) for _ in range(4)) + "-" + "".join(
        secrets.choice(ALPHABET) for _ in range(4))
    norm = normalize(code)
    if len(norm) < 6:
        sys.exit("Der Code ist zu kurz (mindestens 6 Buchstaben/Ziffern).")
    h = hashlib.sha256((SALT + norm).encode("utf-8")).hexdigest()
    if any(c.get("hash") == h for c in codes):
        sys.exit("Diesen Code gibt es schon.")
    cid = a.id or "code%d_%s" % (a.coins, secrets.token_hex(3))
    if not re.fullmatch(r"[a-z0-9_]{1,32}", cid) or any(c.get("id") == cid for c in codes):
        sys.exit("Die Id ist ungültig oder schon vergeben (nur a-z, 0-9, _).")
    entry = {"id": cid, "hash": h, "coins": a.coins}
    if a.item:
        entry["item"] = a.item
    if a.max_uses:
        entry["maxUses"] = a.max_uses
    if a.expires:
        entry["expires"] = a.expires
    if a.public:
        entry["public"] = True
        entry["code"] = code  # nur öffentliche Codes stehen im Klartext drin (für die Website)
    codes.append(entry)
    with open(a.file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("Neuer Code:  %s" % code)
    print("Coins:       %d" % a.coins)
    if a.item:
        print("Item:        %s (exklusiv)" % a.item)
    print("Eingetragen in %s (Id %s). Jetzt codes.json auf GitHub hochladen." % (a.file, cid))


if __name__ == "__main__":
    main()
