"""Tests for the versioned default config loader."""
import json

from src.config import default_config
from src.config.default_config import (config_path, load_defaults,
                                       reset_defaults, setting)


def teardown_function():
    reset_defaults()


def test_defaults_are_offline_safe():
    d = load_defaults()
    assert d["autofill_enabled"] is False
    assert d["maps_key"] == ""
    assert d["maps_autofill"] is True
    assert len(d["model_chain"]) >= 2
    assert d["api_base"].startswith("https://")


def test_config_path_points_at_bundled_file():
    p = config_path()
    assert p.name == "default_config.json"
    assert p.exists()


def test_file_is_valid_json_with_schema_version():
    data = json.loads(config_path().read_text(encoding="utf-8"))
    assert data["schema_version"]
    assert isinstance(data["model_chain"], list)


def test_setting_returns_value():
    assert setting("browser_kind") == "auto"


def test_setting_unknown_key_returns_none():
    assert setting("no_such_key") is None


def test_setting_unknown_key_honours_default():
    assert setting("no_such_key", "fallback") == "fallback"


def test_missing_file_falls_back_to_builtin(tmp_path, monkeypatch):
    monkeypatch.setattr(default_config, "config_path",
                        lambda: tmp_path / "absent.json")
    reset_defaults()
    d = load_defaults()
    assert d["model_chain"]
    assert setting("browser_kind") == "auto"


def test_malformed_file_falls_back_to_builtin(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    monkeypatch.setattr(default_config, "config_path", lambda: bad)
    reset_defaults()
    assert setting("browser_kind") == "auto"


def test_photo_limits_are_sane():
    d = load_defaults()
    assert 0 < d["max_photo_mb"] <= 50
    assert 0 < d["max_photos_per_property"] <= 50
    assert d["thumbnail_height"] >= 64
