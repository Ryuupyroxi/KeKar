#!/usr/bin/env bash
# build.sh - Linux build
#
# Uses the project venv (.venv). On Debian/MX the system Python is externally
# managed (PEP 668), so a bare `pip install` fails; the venv avoids that and
# keeps the build reproducible. --system-site-packages lets us reuse an
# already-installed PyQt6 instead of downloading Qt again.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating .venv ..."
  python3 -m venv --system-site-packages .venv
fi

.venv/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m PyInstaller KeKar.spec --noconfirm
.venv/bin/python tools/make_usb_package.py --platform linux --source dist/KeKar --out out/KeKar_Linux
.venv/bin/python tools/verify_usb.py out/KeKar_Linux --platform linux
echo "Built: out/KeKar_Linux/"
