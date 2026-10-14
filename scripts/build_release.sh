#!/usr/bin/env bash
# Build dist/canvas-step-wedge-<version>.zip: the plugin folder, install script,
# README and CHANGELOG. The version comes from __version__ in the plugin.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="$(python3 -c 'import re;print(re.search(r"__version__ = \"(.+?)\"",open("canvas-step-wedge/canvas-step-wedge.py").read()).group(1))')"
NAME="canvas-step-wedge-$VERSION"
OUT="dist/$NAME"
rm -rf "$OUT" "$OUT.zip"; mkdir -p "$OUT/scripts"

cp -R canvas-step-wedge "$OUT/canvas-step-wedge"
cp scripts/install.sh "$OUT/scripts/"
cp README.md CHANGELOG.md LICENSE "$OUT/"
find "$OUT" \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \) -prune -exec rm -rf {} +
chmod +x "$OUT/canvas-step-wedge/canvas-step-wedge.py" "$OUT/scripts/install.sh"

if grep -rIl "/Users/" "$OUT" >/dev/null 2>&1; then
  echo "ERROR: a personal absolute path leaked into the release:" >&2
  grep -rIn "/Users/" "$OUT" >&2; exit 1
fi
(cd dist && zip -qrX "$NAME.zip" "$NAME")
echo "Built dist/$NAME.zip"
shasum -a 256 "dist/$NAME.zip"
