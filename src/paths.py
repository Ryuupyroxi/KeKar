"""Portable path resolution for KeKar.

This is the ONLY module that knows where data lives. Everything else imports
from here, so the whole app can be relocated (USB drive, different drive letter,
different OS) by changing this file.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "KeKar"


def exe_dir() -> Path:
    """Directory containing the running executable (or the source tree in dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _os_fallback() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def _writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / f".kekar_write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """Resolve the portable data directory. First match wins.

    Order: KEKAR_DATA_DIR env var -> the portable KeKarData location ->
           OS app-config fallback.

    The portable location depends on how the app is running: a frozen build
    keeps KeKarData beside the platform folder, while a source checkout keeps
    it inside the project.
    """
    env = os.environ.get("KEKAR_DATA_DIR")
    if env:
        candidate = Path(env).expanduser().resolve()
        if _writable(candidate):
            return candidate
        raise RuntimeError(f"KEKAR_DATA_DIR is set but not writable: {candidate}")

    ex = exe_dir()
    if getattr(sys, "frozen", False):
        # Frozen build: KeKarData sits beside the platform folder, so the
        # repo build uses dist/KeKarData and a USB package uses <usb>/KeKarData.
        candidates = (ex.parent / "KeKarData", ex / "KeKarData")
    else:
        # Source checkout: keep the data inside the project. The old code also
        # tried ex.parent, which put it in the *parent* of the project
        # (Documents/KeKarData) and scattered data across two locations.
        candidates = (ex / "KeKarData",)
    for candidate in candidates:
        if _writable(candidate):
            return candidate

    fallback = _os_fallback()
    if _writable(fallback):
        return fallback
    raise RuntimeError("No writable data directory found")


def database_path() -> Path:
    return data_dir() / "database.db"


def photos_dir() -> Path:
    return data_dir() / "photos"


def applicants_dir() -> Path:
    return data_dir() / "applicants"


def memory_dir() -> Path:
    return data_dir() / "memory"


def config_dir() -> Path:
    return data_dir() / "config"


def backups_dir() -> Path:
    return data_dir() / "backups"


def calendar_dir() -> Path:
    """Where exported iCal feeds are written, for upload to a portal."""
    return data_dir() / "calendar"


def logs_dir() -> Path:
    return data_dir() / "logs"


def browser_profile_dir() -> Path:
    return data_dir() / "browser_profile"


def demo_database_path() -> Path:
    """The demo database, inside the real data directory but separate from the
    user's own database so demo mode can never write to it."""
    return data_dir() / "demo" / "database.db"


def resource_path(*parts: str) -> Path:
    """Locate a shipped resource, in a source checkout or inside a bundle.

    `KeKar.spec` copies `src/resources` to `resources/`, so a frozen build reads
    them from `_MEIPASS`. Returns the path whether or not it exists — callers
    decide how to degrade — so a missing asset is a visible fallback rather than
    an import-time crash.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS",
                            Path(sys.executable).resolve().parent))
        bundled = base / "resources" / Path(*parts)
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "resources" / Path(*parts)


def icon_path() -> Path:
    return resource_path("icons", "kekar.ico")


def logo_path() -> Path:
    return resource_path("icons", "kekar-logo.png")
