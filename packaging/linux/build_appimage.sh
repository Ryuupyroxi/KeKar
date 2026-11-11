#!/usr/bin/env bash
# packaging/linux/build_appimage.sh
# Builds a self-contained AppImage from dist/KeKar. Requires linuxdeploy.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$HERE/appdir"
rm -rf "$BUILD" && mkdir -p "$BUILD"
cp -a "$HERE/../../dist/KeKar/." "$BUILD/"
cp "$HERE/kekar.desktop" "$BUILD/"
[ -f "$HERE/kekar.png" ] && cp "$HERE/kekar.png" "$BUILD/" || true

linuxdeploy --appdir "$BUILD" --output appimage
echo "AppImage built."
