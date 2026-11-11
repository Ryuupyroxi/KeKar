import pytest

from src.services.browser.cdp_client import CDPClient, CDPUnavailable


def test_connect_fails_cleanly_without_browser():
    client = CDPClient(port=59999)
    with pytest.raises(CDPUnavailable):
        client.connect()


def test_close_is_safe_when_never_connected():
    CDPClient(port=59999).close()
