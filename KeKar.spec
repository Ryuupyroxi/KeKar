# KeKar.spec
# Build:  pyinstaller KeKar.spec --noconfirm
# Works on both Windows and Linux; PyInstaller detects the host OS.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / "config"), "config"),
    (str(ROOT / "src" / "resources"), "resources"),
    # schema.sql is embedded in Python (src/data/_schema_embedded.py), so it is
    # deliberately NOT listed here — shipping it would create a second copy that
    # could drift from the authoritative embedded one.
]
binaries = []
hiddenimports = []
excludes = ["tkinter", "matplotlib", "numpy", "pandas", "PySide6", "pytest"]

for pkg in ("PyQt6", "playwright", "cryptography", "httpx", "PIL"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

for pkg in ("PyQt6", "playwright"):
    try:
        for binaries_, datas_, hiddenimports_ in collect_all(pkg):
            binaries += binaries_
            datas += datas_
            hiddenimports += hiddenimports_
    except Exception:
        pass

a = Analysis(
    ["src/main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon = ROOT / "src" / "resources" / "icons" / "kekar.ico"
_exe_kwargs = {}
if _icon.exists():
    _exe_kwargs["icon"] = str(_icon)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KeKar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX triggers AV false positives on Windows
    console=False,      # GUI app: no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    **_exe_kwargs,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KeKar",
)
