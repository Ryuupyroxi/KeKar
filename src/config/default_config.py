"""Versioned default configuration.

Reads config/default_config.json, which ships inside the bundle. Every value in
this file is a safe default — nothing here is secret, and a missing or malformed
file must never stop the app from starting, so failures fall back to the
built-in DEFAULTS below.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CONFIG_SCHEMA_VERSION = "2026-11-11"

DEFAULTS = {
    "schema_version": CONFIG_SCHEMA_VERSION,
    "api_base": "https://openrouter.ai/api/v1",
    "model_chain": [
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-flash-1.5",
        "nousresearch/hermes-3-llama-3.1-8b",
    ],
    "request_timeout_s": 45,
    "max_agent_steps": 8,
    "browser_kind": "auto",
    "autofill_enabled": False,
    "backup_keep_days": 30,
    "photo_max_dimension": 1600,
    "photo_jpeg_quality": 82,
    "thumbnail_height": 140,
    "max_photos_per_property": 12,
    "max_photo_mb": 20,
    "chat_history_limit": 200,
    "log_max_bytes": 2_000_000,
    "log_backup_count": 3,
}

_CONFIG_CACHE: dict | None = None


def config_path() -> Path:
    """Locate config/default_config.json in dev and inside a bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS",
                            Path(sys.executable).resolve().parent))
        bundled = base / "config" / "default_config.json"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[2] / "config" / "default_config.json"


def load_defaults(path: Path | None = None) -> dict:
    """Read the default config, falling back to the built-in defaults."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        data = json.loads((path or config_path()).read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema_version"):
            merged = dict(DEFAULTS)
            merged.update(data)
            _CONFIG_CACHE = merged
            return _CONFIG_CACHE
    except (OSError, ValueError, TypeError):
        pass
    _CONFIG_CACHE = dict(DEFAULTS)
    return _CONFIG_CACHE


def reset_defaults() -> None:
    """Drop the cached config (used by tests)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


def setting(key: str, default=None):
    """Return one configured value, or `default` when the key is unknown."""
    return load_defaults().get(key, default)
