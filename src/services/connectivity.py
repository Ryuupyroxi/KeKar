"""Reachability check for the AI provider.

Used to drive the offline banner. This is a plain TCP connect, not an API
call, so it costs nothing and never sends the API key.
"""
from __future__ import annotations

import socket
from urllib.parse import urlparse


def provider_reachable(api_base: str, timeout: float = 4.0) -> bool:
    """True when the provider's host accepts a TCP connection."""
    parsed = urlparse(api_base)
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
