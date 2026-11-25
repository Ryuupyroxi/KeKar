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
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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

README_POINTER = """This portable app includes INSTRUCTIONS.txt with setup, data-location,
assistant and troubleshooting details. Start there.
"""

INSTRUCTIONS = """KEKAR — QUICK START INSTRUCTIONS
=================================

This folder is a portable application. Keep the whole folder together; your
data stays with it.

WINDOWS
-------
1. Open the package folder and double-click KeKar.bat.
2. If Windows says "Windows protected your PC", choose More info -> Run anyway.
3. Optional: right-click KeKar.bat and choose Send to > Desktop (create shortcut).

LINUX
-----
1. In a terminal in this folder run:
       chmod +x KeKar.sh
       ./KeKar.sh
2. Optional desktop/menu launcher:
       python3 install_linux.py --desktop
   Run it again if the drive mount point changes.

YOUR DATA
---------
Your own data starts empty. The guided tour uses a separate demo database.
Everything you save lives in KeKarData beside the launcher. Copy the whole
folder to back it up.

ASSISTANT
---------
The AI assistant is already configured. Ask it questions in the chat pane.
It is the only part of this app that uses the internet. Keep this folder
private — its configuration includes access to the assistant account.

TROUBLESHOOTING
---------------
App will not open  Check that you launched the file beside KeKarData.
Slow on USB        Use a USB 3.0 port (blue), not a hub.
Photos won't add   Use .jpg or .png under 20 MB.
Windows warning    More info -> Run anyway.

Need help? Contact whoever supplied this copy.
"""

def _lite(text: str) -> str:
    """Swap product names but never the shared KeKarData folder."""
    return re.sub(r"KeKar(?!Data)", "KeKarLite", text)


def bat_for(variant: str) -> str:
    return BAT if variant == "full" else _lite(BAT)


def sh_for(variant: str) -> str:
    return SH if variant == "full" else _lite(SH)


def readme_for(variant: str) -> str:
    return README_POINTER


def instructions_for(variant: str) -> str:
    if variant == "lite":
        return INSTRUCTIONS.replace("KEKAR", "KEKAR LITE")
    return INSTRUCTIONS


DATA_SUBDIRS = ("photos", "applicants", "memory", "config", "backups", "logs")


def make_platform_package(platform: str, source: Path, out: Path,
                          variant: str = "full") -> Path:
    if not source.exists():
        sys.exit(f"source build not found: {source}")
    # Clear the previous package so nothing stale survives (an old
    # KeKar.desktop, a removed launcher, an outdated README).
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    name = "KeKarLite" if variant == "lite" else "KeKar"
    target = out / f"{name}_{platform.capitalize()}"
    shutil.copytree(source, target)
    if platform == "windows":
        _stage_icon(target)
    _write_launchers(out, variant, platform)
    return out


def _stage_icon(target: Path) -> None:
    """Copy the kekar .ico to the Windows package root.

    The NSIS installer points its shortcuts at $INSTDIR\\kekar.ico. The same
    .ico also ships inside _internal/resources/icons, but a stable
    package-root path keeps the installer independent of PyInstaller's
    internal layout.
    """
    source = ROOT / "src" / "resources" / "icons" / "kekar.ico"
    if source.exists():
        shutil.copy2(source, target / "kekar.ico")


def combine(linux_dir: Path, windows_dir: Path, out: Path,
            variant: str = "full") -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    name = "KeKarLite" if variant == "lite" else "KeKar"
    if windows_dir.exists():
        shutil.copytree(windows_dir, out / f"{name}_Windows")
        _stage_icon(out / f"{name}_Windows")
    if linux_dir.exists():
        shutil.copytree(linux_dir, out / f"{name}_Linux")
    _write_launchers(out, variant)
    return out


def _write_launchers(out: Path, variant: str = "full",
                     platform: str | None = None) -> Path:
    name = "KeKarLite" if variant == "lite" else "KeKar"
    if platform in (None, "windows"):
        (out / f"{name}.bat").write_text(bat_for(variant), encoding="utf-8")
    if platform in (None, "linux"):
        sh = out / f"{name}.sh"
        sh.write_text(sh_for(variant), encoding="utf-8")
        sh.chmod(0o755)
        # The one-click installer is Linux-only.
        source = Path(__file__).resolve().parent / "install_linux.py"
        if source.exists():
            shutil.copy2(source, out / "install_linux.py")
            (out / "install_linux.py").chmod(0o755)
    (out / "README.txt").write_text(readme_for(variant), encoding="utf-8")
    (out / "INSTRUCTIONS.txt").write_text(
        instructions_for(variant), encoding="utf-8")

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
    parser.add_argument("--variant", choices=["full", "lite"], default="full")
    parser.add_argument("--combine", action="store_true")
    parser.add_argument("--linux", type=Path)
    parser.add_argument("--windows", type=Path)
    args = parser.parse_args()

    if args.combine:
        combine(args.linux, args.windows, args.out, args.variant)
        print(f"Combined USB package: {args.out}")
    elif args.platform and args.source:
        make_platform_package(args.platform, args.source, args.out,
                              args.variant)
        print(f"Platform package: {args.out}")
    else:
        parser.error("use --combine with --linux/--windows, "
                     "or --platform with --source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
