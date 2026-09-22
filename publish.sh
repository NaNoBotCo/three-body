#!/bin/bash
# Build the site into docs/ — the directory GitHub Pages serves.
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN="${CNAME:-$(head -1 docs/CNAME 2>/dev/null || true)}"
if [ -n "$DOMAIN" ]; then SITE_URL="https://$DOMAIN"; else SITE_URL="https://nanobotco.github.io/three-body"; fi

python3 tests/check_data.py
[ -f build/img/hero.jpg ] || python3 tools/draw.py
SITE_URL="$SITE_URL" python3 tools/build.py

rm -rf docs
mkdir -p docs
cp -R build/site/. docs/
touch docs/.nojekyll
[ -n "$DOMAIN" ] && echo "$DOMAIN" > docs/CNAME

if grep -rl "/Users/" docs >/dev/null 2>&1; then
  echo "REFUSED: host paths found in docs/"; exit 2
fi
python3 tests/check_links.py docs
echo "docs/ built for $SITE_URL — $(find docs -name '*.html' | wc -l | tr -d ' ') pages, $(du -sh docs | cut -f1)"
