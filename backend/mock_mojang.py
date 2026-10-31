#!/usr/bin/env python3
"""Ein falscher Mojang-Session-Server NUR für den lokalen Test (join und hasJoined, wie das echte Protokoll)."""
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

USERS = {"Alice": "11111111111111111111111111111111", "Bob": "22222222222222222222222222222222"}
JOINED = {}  # serverId -> uuid ohne Bindestriche


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path != "/session/minecraft/join":
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        ok = body.get("accessToken") == "token-" + body.get("selectedProfile", "")
        if ok:
            JOINED[body["serverId"]] = body["selectedProfile"]
        self.send_response(204 if ok else 403)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path != "/session/minecraft/hasJoined":
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        q = urllib.parse.parse_qs(p.query)
        name = q.get("username", [""])[0]
        sid = q.get("serverId", [""])[0]
        uid = JOINED.get(sid)
        if uid and USERS.get(name) == uid:
            data = json.dumps({"id": uid, "name": name}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(204); self.send_header("Content-Length", "0"); self.end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
