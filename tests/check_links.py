#!/usr/bin/env python3
"""check_links.py — every internal href and src in a built directory resolves to a file.
    python3 tests/check_links.py docs"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1] if len(sys.argv) > 1 else "docs").resolve()
bad = []
n = 0
for p in root.rglob("*.html"):
    txt = p.read_text(encoding="utf-8")
    for m in re.finditer(r'(?:href|src)="([^"#]+)(?:#[^"]*)?"|url\(([^)]+)\)', txt):
        u = m.group(1) or m.group(2)
        if not u or u.startswith(("http", "mailto:", "data:", "//")):
            continue
        n += 1
        t = (p.parent / unquote(u)).resolve()
        if t.is_dir():
            t = t / "index.html"
        if not t.exists():
            bad.append(f"{p.relative_to(root)} → {u}")
if bad:
    print("\n".join(bad)); sys.exit(1)
print(f"links ok: {n} internal links in {len(list(root.rglob('*.html')))} pages")
