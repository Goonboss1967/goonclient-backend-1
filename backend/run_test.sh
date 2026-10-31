#!/usr/bin/env bash
# Startet falschen Mojang-Server + Backend lokal und lässt den Java-Client dagegen laufen.
# Aufruf im Projektordner:  bash tools/backend/run_test.sh <pfad-zu-gson.jar>
set -e
GSON="${1:?Pfad zu gson.jar angeben}"
cd "$(dirname "$0")/../.."
OUT=build/it; rm -rf "$OUT"; mkdir -p "$OUT"
javac -d "$OUT" -cp "$GSON" src/main/java/com/goonclient/network/CosmeticsRules.java \
  src/client/java/com/goonclient/backend/CosmeticsData.java src/client/java/com/goonclient/backend/BackendApi.java tools/BackendIntegrationTest.java
python3 tools/backend/mock_mojang.py 18081 & MOJ=$!
python3 tools/backend/server.py --port 18080 --db "$OUT/test.db" --mojang http://127.0.0.1:18081 & SRV=$!
trap 'kill $MOJ $SRV 2>/dev/null' EXIT
sleep 1.5
java -cp "$OUT:$GSON" BackendIntegrationTest http://127.0.0.1:18080 http://127.0.0.1:18081
