#!/usr/bin/env python3
"""Assemble the dual-platform KeKar USB layout.

Layout produced:
    <out>/
    ├── KeKar_Windows/        (Windows build: KeKar.exe + _internal/)
    ├── KeKar_Linux/          (Linux build: KeKar + _internal/)
    ├── KeKarData/            (shared, populated on first run)
    ├── KeKar.bat             (Windows launcher)
    ├── KeKar.sh              (Linux launcher)
    └── README.txt
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BAT = """@echo off
rem KeKar launcher (Windows)
rem
rem Double-click this file to open KeKar. It works from any drive letter and
rem leaves nothing behind on the computer except the KeKarData folder on this
rem drive.
setlocal
set "HERE=%~dp0"

if not exist "%HERE%KeKar_Windows\\KeKar.exe" (
  echo.
  echo  KeKar was not found on this drive.
  echo  Look for the folder named KeKar_Windows and try again.
  echo.
  pause
  exit /b 1
)

start "" "%HERE%KeKar_Windows\\KeKar.exe"
endlocal
"""

SH = """#!/bin/sh
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
"""

# The package ships no .desktop file of its own: the Desktop Entry
# Specification cannot express a portable Exec, so a .desktop baked into the
# package either points at a machine-specific path or fails validation.
# install_linux.py (copied into the package) writes a correct one with the
# real path, an icon, and a Desktop shortcut. Double-clicking KeKar.sh is the
# zero-setup path.

README = """KEKAR PROPERTY MANAGER
======================

To open KeKar:
  On Windows:  double-click  KeKar.bat
  On Linux:    double-click  KeKar.sh  (or run ./KeKar.sh in a terminal)

For a one-click icon on Linux (application menu and Desktop):
  Run:  python3 install_linux.py --desktop
  (or simply:  ./install_linux.py --desktop)
This writes a proper launcher with the KeKar icon. If the drive's mount
point changes, run it again after plugging the drive in.

Your properties, photos, and notes are stored in the KeKarData folder on this
drive. They never leave this drive unless you email or copy them yourself.

If Windows says "Windows protected your PC":
  Click "More info", then "Run anyway". This happens because the app is new and
  not yet signed. It is safe.

If the app will not start:
  - Try a different USB port (use a USB 3.0 port, usually blue).
  - Make sure the drive is plugged in before you double-click.
  - Right-click KeKar.bat and choose "Run as administrator" once.

TROUBLESHOOTING
---------------
Problem                          What to do
-------------------------------- ------------------------------------------
"Windows protected your PC"      More info -> Run anyway
App opens then closes             Plug the drive in again, then retry
Chat says it can't connect        Check the computer's internet, then retry
Photos won't add                  Use .jpg or .png, under 20 MB each
Drive is slow                     Use a USB 3.0 port (blue), not a hub
Forgot which drive                Look for the folder named KeKarData

Need help? Contact your family's KeKar helper.
"""

DATA_SUBDIRS = ("photos", "applicants", "memory", "config", "backups", "logs")


def make_platform_package(platform: str, source: Path, out: Path) -> Path:
    if not source.exists():
        sys.exit(f"source build not found: {source}")
    # Clear the previous package so nothing stale survives (an old
    # KeKar.desktop, a removed launcher, an outdated README).
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"KeKar_{platform.capitalize()}"
    shutil.copytree(source, target)
    _write_launchers(out)
    return out


def combine(linux_dir: Path, windows_dir: Path, out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if windows_dir.exists():
        shutil.copytree(windows_dir, out / "KeKar_Windows")
    if linux_dir.exists():
        shutil.copytree(linux_dir, out / "KeKar_Linux")
    _write_launchers(out)
    return out


def _write_launchers(out: Path) -> Path:
    (out / "KeKar.bat").write_text(BAT, encoding="utf-8")
    sh = out / "KeKar.sh"
    sh.write_text(SH, encoding="utf-8")
    sh.chmod(0o755)
    (out / "README.txt").write_text(README, encoding="utf-8")

    # The one-click installer travels with the package. It auto-detects the
    # binary inside KeKar_Linux/ and writes a validated .desktop entry.
    source = Path(__file__).resolve().parent / "install_linux.py"
    if source.exists():
        shutil.copy2(source, out / "install_linux.py")
        (out / "install_linux.py").chmod(0o755)

    data = out / "KeKarData"
    data.mkdir(exist_ok=True)
    for sub in DATA_SUBDIRS:
        (data / sub).mkdir(exist_ok=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["linux", "windows"])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--combine", action="store_true")
    parser.add_argument("--linux", type=Path)
    parser.add_argument("--windows", type=Path)
    args = parser.parse_args()

    if args.combine:
        combine(args.linux, args.windows, args.out)
        print(f"Combined USB package: {args.out}")
    elif args.platform and args.source:
        make_platform_package(args.platform, args.source, args.out)
        print(f"Platform package: {args.out}")
    else:
        parser.error("use --combine with --linux/--windows, "
                     "or --platform with --source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
