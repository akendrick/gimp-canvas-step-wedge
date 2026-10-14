#!/usr/bin/env bash
# Install the Canvas Step Wedge plugin into a GIMP 3 user plug-ins folder.
#
#   scripts/install.sh [--gimp-version 3.2] [--plugins-dir DIR] [--link] [--uninstall]
#
#   --link       symlink instead of copy (development: edits apply live)
#   --uninstall  remove a previously installed copy/link
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(dirname "$HERE")/canvas-step-wedge"
NAME="canvas-step-wedge"
[ -d "$SRC" ] || { echo "Can't find the $NAME folder next to scripts/." >&2; exit 1; }

GIMP_VERSION=""; PLUGINS_DIR=""; LINK=0; UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --gimp-version) GIMP_VERSION="$2"; shift 2 ;;
    --plugins-dir)  PLUGINS_DIR="$2";  shift 2 ;;
    --link) LINK=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$PLUGINS_DIR" ]; then
  case "$(uname -s)" in
    Darwin) BASE="$HOME/Library/Application Support/GIMP" ;;
    Linux)  BASE="$HOME/.config/GIMP" ;;
    *) echo "Unsupported OS for auto-detection; pass --plugins-dir." >&2; exit 1 ;;
  esac
  # No --gimp-version: use the newest existing 3.x profile, else 3.0.
  if [ -z "$GIMP_VERSION" ]; then
    GIMP_VERSION="$(ls -1 "$BASE" 2>/dev/null | grep -E '^3\.[0-9]+$' | sort -t. -k2 -n | tail -1 || true)"
    GIMP_VERSION="${GIMP_VERSION:-3.0}"
  fi
  PLUGINS_DIR="$BASE/$GIMP_VERSION/plug-ins"
fi
DEST="$PLUGINS_DIR/$NAME"

if [ "$UNINSTALL" = 1 ]; then rm -rf "$DEST"; echo "Removed $DEST"; exit 0; fi

mkdir -p "$PLUGINS_DIR"
rm -rf "$DEST"
if [ "$LINK" = 1 ]; then
  ln -s "$SRC" "$DEST"; echo "Linked $DEST -> $SRC"
else
  cp -R "$SRC" "$DEST"
  find "$DEST" \( -name '__pycache__' -o -name '.DS_Store' \) -prune -exec rm -rf {} +
  echo "Copied to $DEST"
fi
chmod +x "$SRC/$NAME.py"
echo "Done. Restart GIMP, then look for:  Colors > Canvas Step Wedge..."
echo "(Installed into: $DEST -- pass --gimp-version / --plugins-dir to change.)"
