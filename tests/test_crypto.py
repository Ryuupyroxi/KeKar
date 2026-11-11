from src.config import crypto


def test_roundtrip():
    key = crypto.load_app_key()
    blob = crypto.encrypt(b"sk-test-123", key)
    assert blob != b"sk-test-123"
    assert crypto.decrypt(blob, key) == b"sk-test-123"


def test_wrong_key_fails():
    key = crypto.load_app_key()
    blob = crypto.encrypt(b"secret", key)
    try:
        crypto.decrypt(blob, b"0" * 32)
        failed = False
    except Exception:
        failed = True
    assert failed


def test_passphrase_derivation_is_deterministic():
    a = crypto.derive_key("hunter2", b"0123456789ab")
    b = crypto.derive_key("hunter2", b"0123456789ab")
    assert a == b and len(a) == 32
