#!/usr/bin/env python3
"""serve.py — serve docs/ locally at the path the host mounts it on.
    python3 tools/serve.py [port]     (default 8846)  →  http://127.0.0.1:8846/three-body/
"""
from __future__ import annotations

import http.server
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PREFIX = "/three-body"


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DOCS), **k)

    def translate_path(self, path):
        if path == "/" or path == PREFIX:
            path = PREFIX + "/"
        if path.startswith(PREFIX + "/"):
            path = path[len(PREFIX):]
        return super().translate_path(path)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8846
    if not (DOCS / "index.html").exists():
        print("no docs/ yet — run ./publish.sh")
        sys.exit(1)
    print(f"http://127.0.0.1:{port}{PREFIX}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
