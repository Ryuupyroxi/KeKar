# build.ps1 - Windows build
#
# Mirrors build.sh: uses a project-local venv so the build is reproducible and
# does not depend on what is installed globally.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv ..."
    python -m venv .venv
}

.venv\Scripts\python.exe -m pip install -q -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m PyInstaller KeKar.spec --noconfirm
.venv\Scripts\python.exe tools\make_usb_package.py --platform windows --source dist\KeKar --out out\KeKar_Windows
.venv\Scripts\python.exe tools\verify_usb.py out\KeKar_Windows --platform windows
Write-Host "Built: out\KeKar_Windows\"
