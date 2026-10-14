#!/usr/bin/env bash
# Run tests/integration/manual_*.py inside headless GIMP 3, using a throwaway
# GIMP profile with the plugin installed so your real GIMP setup is untouched.
# Uses gimp-console: the GUI binary crashes in -i mode on recent macOS.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

if [ -z "${GIMP_BIN:-}" ]; then
  for c in /Applications/GIMP.app/Contents/MacOS/gimp-console \
           "$(command -v gimp-console 2>/dev/null || true)"; do
    [ -n "$c" ] && [ -x "$c" ] && { GIMP_BIN="$c"; break; }
  done
fi
[ -x "${GIMP_BIN:-}" ] || { echo "gimp-console not found; set GIMP_BIN." >&2; exit 1; }

PROFILE="$(mktemp -d)"; trap 'rm -rf "$PROFILE"' EXIT
mkdir -p "$PROFILE/plug-ins"
cp -R canvas-step-wedge "$PROFILE/plug-ins/"; chmod +x "$PROFILE/plug-ins/canvas-step-wedge/canvas-step-wedge.py"
export WEDGE_ROOT="$ROOT" GIMP3_DIRECTORY="$PROFILE"

fail=0
for t in tests/integration/manual_*.py; do
  out="$("$GIMP_BIN" -i -s --batch-interpreter=python-fu-eval -b "$(cat "$t")" --quit 2>&1 || true)"
  # Anchor on a whole output line and reject tracebacks: a failure traceback
  # echoes the script's source, which contains the print("..._PASSED") text.
  if echo "$out" | grep -qE '^[A-Z0-9_]+_PASSED$' && ! echo "$out" | grep -q 'Traceback'; then echo "PASS  $t"
  else echo "FAIL  $t"; echo "$out" | tail -25; fail=1; fi
done
exit $fail
