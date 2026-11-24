import json

from src.config.settings import Settings


def test_defaults_are_offline_safe():
    s = Settings()
    assert s.is_configured() is False
    assert s.autofill_enabled is False
    assert s.maps_key == ""
    assert s.maps_autofill is True
    assert len(s.model_chain) >= 2


def test_maps_settings_roundtrip():
    s = Settings(maps_key="maps-secret", maps_autofill=False)
    s.save()
    loaded = Settings.load()
    assert loaded.maps_key == "maps-secret"
    assert loaded.maps_autofill is False


def test_old_settings_files_get_the_new_defaults(tmp_path, monkeypatch):
    """A settings file written before Maps support still loads."""
    from src.config import crypto

    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path / "KeKarData"))
    old = {"api_key": "key", "autofill_enabled": False}
    out = tmp_path / "KeKarData" / "config"
    out.mkdir(parents=True)
    (out / "settings.enc").write_bytes(
        crypto.encrypt(json.dumps(old).encode("utf-8"),
                       crypto.load_app_key()))
    loaded = Settings.load()
    assert loaded.maps_key == ""
    assert loaded.maps_autofill is True


def test_save_and_load_roundtrip():
    s = Settings(api_key="sk-test-key", model_chain=["a", "b"])
    s.save()
    loaded = Settings.load()
    assert loaded.api_key == "sk-test-key"
    assert loaded.model_chain == ["a", "b"]


def test_passphrase_mode_requires_prompt():
    s = Settings(api_key="sk-test", passphrase_protected=True)
    try:
        s.save()
        failed = False
    except RuntimeError:
        failed = True
    assert failed
