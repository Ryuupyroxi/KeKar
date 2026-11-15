"""Password hashing and session tokens.

PBKDF2-HMAC-SHA256 with a per-password random salt, using `cryptography` —
which KeKar already ships, so no new dependency. Passwords are never stored in
plaintext or in a reversible form, and the comparison is done by `cryptography`
rather than by comparing strings.
"""
from __future__ import annotations

import base64
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

#: OWASP's 2023 guidance for PBKDF2-HMAC-SHA256.
ITERATIONS = 310_000
SALT_BYTES = 16
KEY_BYTES = 32
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    """Return `pbkdf2:<iterations>:<salt>:<digest>`, base64-encoded parts."""
    salt = secrets.token_bytes(SALT_BYTES)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_BYTES,
                     salt=salt, iterations=ITERATIONS)
    digest = kdf.derive(password.encode("utf-8"))
    return ":".join((
        "pbkdf2", str(ITERATIONS),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ))


def verify_password(password: str, stored: str) -> bool:
    """True only if `password` matches the stored hash.

    Any malformed hash returns False rather than raising, so a corrupted
    database cannot turn into a traceback in the login dialog.
    """
    try:
        scheme, iterations, salt_b64, digest_b64 = stored.split(":")
        if scheme != "pbkdf2":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=len(expected),
                         salt=salt, iterations=int(iterations))
        kdf.verify(password.encode("utf-8"), expected)
        return True
    except (InvalidKey, ValueError, TypeError, KeyError):
        return False


def new_session_token() -> str:
    """An unguessable session token. Stored hashed nowhere — it is the secret."""
    return secrets.token_urlsafe(32)


def session_expiry(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return (now + timedelta(days=SESSION_DAYS)).isoformat()


def is_expired(expires_at: str, now: datetime | None = None) -> bool:
    """Compare an ISO timestamp to now. A malformed value counts as expired."""
    now = now or datetime.now(timezone.utc)
    try:
        ends = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    return ends <= now
