"""AES-256-GCM encryption for the local settings file.

Two modes:
  * app-key mode   - a random 32-byte key stored in config/app.key. Zero-setup,
                     but only obfuscates the key against a casual reader.
  * passphrase mode - key derived from a user passphrase via PBKDF2-SHA256.
                     Use this when the drive might be lost or shared.
"""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..paths import config_dir

_KEY_LEN = 32
_NONCE_LEN = 12
_PBKDF2_ITERS = 600_000


def derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=_KEY_LEN,
                     salt=salt, iterations=_PBKDF2_ITERS)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    nonce = os.urandom(_NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt(blob: bytes, key: bytes) -> bytes:
    nonce, ciphertext = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def app_key_path() -> Path:
    return config_dir() / "app.key"


def load_app_key() -> bytes:
    path = app_key_path()
    if path.exists():
        return path.read_bytes()
    key = os.urandom(_KEY_LEN)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # Windows has no POSIX mode bits; best effort only
    return key
