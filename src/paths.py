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

    Order: KEKAR_DATA_DIR env var -> <exe_dir>/../KeKarData ->
           <exe_dir>/KeKarData -> OS app-config fallback.
    Raises RuntimeError if nothing is writable.
    """
    env = os.environ.get("KEKAR_DATA_DIR")
    if env:
        candidate = Path(env).expanduser().resolve()
        if _writable(candidate):
            return candidate
        raise RuntimeError(f"KEKAR_DATA_DIR is set but not writable: {candidate}")

    ex = exe_dir()
    for candidate in (ex.parent / "KeKarData", ex / "KeKarData"):
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


def logs_dir() -> Path:
    return data_dir() / "logs"


def browser_profile_dir() -> Path:
    return data_dir() / "browser_profile"
