#!/bin/sh
# Build a .deb package for uscraper. Run from project root.
# Use: make dist-deb  (uses venv) or ./packaging/build_deb.sh

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.venv/bin/python3" ]; then
  PY="$ROOT/.venv/bin/python3"
else
  PY=python3
fi

# Build sdist if missing
if [ ! -f dist/uscraper-*.tar.gz ]; then
  echo "Building source distribution..."
  "$PY" -m pip install -q build
  "$PY" -m build --sdist
fi

SDIST=$(ls dist/uscraper-*.tar.gz 2>/dev/null | head -1)
if [ -z "$SDIST" ]; then
  echo "No sdist found in dist/. Run: $PY -m build --sdist" 1>&2
  exit 1
fi

echo "Using $SDIST"
"$PY" -m pip install -q stdeb

# Build .deb into packaging/deb_dist
mkdir -p packaging/deb_dist
rm -rf packaging/deb_dist/uscraper-* 2>/dev/null || true
cd packaging/deb_dist
"$PY" -m stdeb.command.py2dsc "$ROOT/$SDIST"
# py2dsc creates e.g. uscraper-0.1.0
DIR=$(ls -d uscraper-* 2>/dev/null | head -1)
if [ -n "$DIR" ] && [ -d "$DIR" ]; then
  cd "$DIR"
  dpkg-buildpackage -uc -us
  cd ..
  echo "Built: packaging/deb_dist/python3-uscraper_*.deb"
else
  echo "stdeb did not create expected directory." 1>&2
  exit 1
fi
