#!/usr/bin/env bash
# copy_to_usb.sh <USB_MOUNT_POINT> <PACKAGE_DIR>
#
# Copies a KeKar package to a flash drive and verifies it by file count and
# checksum. A plain `cp -r` of a PyInstaller one-folder build onto a FAT
# filesystem is thousands of small writes; an interrupted copy leaves a silently
# broken app. Always use this script, never a bare copy.
set -euo pipefail
DEST="${1:?usage: copy_to_usb.sh <usb-mount-point> <package-dir>}"
SRC="${2:?usage: copy_to_usb.sh <usb-mount-point> <package-dir>}"
[ -d "$DEST" ] || { echo "Not a directory: $DEST"; exit 1; }
[ -d "$SRC" ] || { echo "No such package: $SRC"; exit 1; }

WORK="${TMPDIR:-${PWD}/.kekar-tmp}"
mkdir -p "$WORK"

echo "Copying $SRC -> $DEST (several minutes on a slow drive)..."
cp -a "$SRC"/. "$DEST"/
sync

echo "Verifying..."
EXPECTED=$(find "$SRC" -type f | wc -l)
ACTUAL=$(find "$DEST" -type f | wc -l)
if [ "$EXPECTED" -ne "$ACTUAL" ]; then
  echo "MISMATCH: expected $EXPECTED files, found $ACTUAL. Copy again."
  exit 1
fi

( cd "$SRC" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$WORK/kekar_src.sha"
( cd "$DEST" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$WORK/kekar_dst.sha"
if ! diff -q "$WORK/kekar_src.sha" "$WORK/kekar_dst.sha" >/dev/null; then
  echo "CHECKSUM MISMATCH. Copy again."
  exit 1
fi
rm -f "$WORK/kekar_src.sha" "$WORK/kekar_dst.sha"
echo "Verified: $ACTUAL files match. Safe to eject."
