"""Tests for tools/seed_first_run.py — the zero-setup key seeder."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "seed_first_run", ROOT / "tools" / "seed_first_run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_first_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tool():
    return _load_tool()


def _run(tool, monkeypatch, data_dir, key, *extra):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data_dir))
    argv = ["seed_first_run", "--data-dir", str(data_dir), "--key", key]
    argv.extend(extra)
    monkeypatch.setattr(sys, "argv", argv)
    return tool.main()


def test_seeds_key_into_empty_data_dir(tool, monkeypatch, tmp_path):
    data = tmp_path / "KeKarData"
    assert _run(tool, monkeypatch, data, "sk-test-abc123def456") == 0
    assert (data / "config" / "settings.enc").is_file()
    assert (data / "config" / "app.key").is_file()


def test_seeded_settings_are_loadable(tool, monkeypatch, tmp_path):
    from src.config.settings import Settings

    data = tmp_path / "KeKarData"
    _run(tool, monkeypatch, data, "sk-test-abc123def456")
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data))
    loaded = Settings.load()
    assert loaded.is_configured() is True
    assert loaded.api_key == "sk-test-abc123def456"


def test_key_is_never_echoed_in_full(tool, monkeypatch, tmp_path, capsys):
    data = tmp_path / "KeKarData"
    key = "sk-supersecret-key-00000000"
    _run(tool, monkeypatch, data, key)
    out = capsys.readouterr().out
    assert key not in out
    assert "..." in out


def test_refuses_to_overwrite_existing_portfolio(tool, monkeypatch, tmp_path):
    from src.data.db import Database
    from src.data.models import Property
    from src.data.property_repo import PropertyRepo

    data = tmp_path / "KeKarData"
    data.mkdir(parents=True)
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data))
    database = Database()
    PropertyRepo(database.conn).create(Property(address="1 Existing St"))
    database.close()

    assert _run(tool, monkeypatch, data, "sk-new-key-11112222") == 1


def test_force_overrides_the_guard(tool, monkeypatch, tmp_path):
    from src.data.db import Database
    from src.data.models import Property
    from src.data.property_repo import PropertyRepo

    data = tmp_path / "KeKarData"
    data.mkdir(parents=True)
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data))
    database = Database()
    PropertyRepo(database.conn).create(Property(address="1 Existing St"))
    database.close()

    assert _run(tool, monkeypatch, data, "sk-new-key-11112222", "--force") == 0


def test_model_chain_override(tool, monkeypatch, tmp_path):
    from src.config.settings import Settings

    data = tmp_path / "KeKarData"
    _run(tool, monkeypatch, data, "sk-test-abc123", "--model-chain",
         "model/a, model/b ,model/c")
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data))
    assert Settings.load().model_chain == ["model/a", "model/b", "model/c"]


def test_warns_on_key_that_does_not_look_like_a_key(tool, monkeypatch, tmp_path,
                                                    capsys):
    data = tmp_path / "KeKarData"
    _run(tool, monkeypatch, data, "not-a-real-key")
    assert "WARNING" in capsys.readouterr().err


def test_seeded_data_dir_skips_the_wizard(tool, monkeypatch, tmp_path):
    """A seeded drive must report is_configured() so main.py skips the wizard."""
    from src.config.settings import Settings

    data = tmp_path / "KeKarData"
    _run(tool, monkeypatch, data, "sk-test-abc123")
    monkeypatch.setenv("KEKAR_DATA_DIR", str(data))
    assert Settings().is_configured() is False      # fresh object
    assert Settings.load().is_configured() is True  # loaded from disk
