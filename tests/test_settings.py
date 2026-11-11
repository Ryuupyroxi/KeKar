from src.config.settings import Settings


def test_defaults_are_offline_safe():
    s = Settings()
    assert s.is_configured() is False
    assert s.autofill_enabled is False
    assert len(s.model_chain) >= 2


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
