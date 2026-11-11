#!/bin/sh
# KeKar launcher (Linux)
#
# Double-click this file, or run:  ./KeKar.sh
# Works from any mount point; all data stays in the KeKarData folder here.
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -x "$HERE/KeKar_Linux/KeKar" ]; then
  echo "KeKar was not found on this drive."
  echo "Look for the folder named KeKar_Linux and try again."
  exit 1
fi

# Qt needs a platform plugin. On a headless machine fall back to offscreen so
# the app starts instead of aborting with "could not connect to display".
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
fi

exec "$HERE/KeKar_Linux/KeKar" "$@"
