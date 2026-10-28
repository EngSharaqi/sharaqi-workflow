#!/usr/bin/env python3
"""Local stand-in for the Anthropic API for preflight.sh: saves each request body and answers
HTTP 400, so `claude -p` stops after its first requests. Nothing leaves the machine and
nothing is billed. Request headers (they carry credentials) are never written.
usage: capture.py <out dir> <port>"""
import http.server
import itertools
import json
import os
import sys

OUT, PORT = sys.argv[1], int(sys.argv[2])
N = itertools.count()


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        with open(os.path.join(OUT, "req-%03d.json" % next(N)), "wb") as fh:
            fh.write(body)
        msg = json.dumps({"type": "error", "error": {"type": "invalid_request_error",
                                                     "message": "preflight capture"}}).encode()
        self.send_response(400)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    do_GET = do_POST

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
