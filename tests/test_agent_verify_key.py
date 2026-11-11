"""Tests for LLMClient.verify_key — the first-run connection check."""
import httpx
import pytest

from src.agent.client import LLMClient
from src.config.settings import Settings


def _client(key="sk-test-key"):
    return LLMClient(Settings(api_key=key))


def _response(status, url="https://example.test/v1/models", method="GET"):
    request = httpx.Request(method, url)
    return httpx.Response(status, request=request, json={})


@pytest.mark.asyncio
async def test_verify_key_accepts_200(monkeypatch):
    async def fake_get(self, url, **kw):
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, msg = await _client().verify_key()
    assert ok is True
    assert "Connected" in msg


@pytest.mark.asyncio
async def test_verify_key_rejects_401(monkeypatch):
    async def fake_get(self, url, **kw):
        return _response(401)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "rejected" in msg


@pytest.mark.asyncio
async def test_verify_key_rejects_403(monkeypatch):
    async def fake_get(self, url, **kw):
        return _response(403)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, _ = await _client().verify_key()
    assert ok is False


@pytest.mark.asyncio
async def test_verify_key_survives_network_failure(monkeypatch):
    async def fake_get(self, url, **kw):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "Could not reach" in msg


@pytest.mark.asyncio
async def test_verify_key_reports_server_error(monkeypatch):
    async def fake_get(self, url, **kw):
        return _response(503)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "503" in msg


@pytest.mark.asyncio
async def test_verify_key_without_a_key_short_circuits(monkeypatch):
    called = []

    async def fake_get(self, url, **kw):
        called.append(True)
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ok, msg = await _client(key="").verify_key()
    assert ok is False
    assert "No API key" in msg
    assert called == []


@pytest.mark.asyncio
async def test_verify_key_sends_the_authorization_header(monkeypatch):
    seen = {}

    async def fake_get(self, url, **kw):
        seen.update(kw.get("headers") or {})
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    await _client("sk-secret-key").verify_key()
    assert seen.get("Authorization") == "Bearer sk-secret-key"


@pytest.mark.asyncio
async def test_verify_key_uses_the_models_endpoint(monkeypatch):
    seen = {}

    async def fake_get(self, url, **kw):
        seen["url"] = url
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    await _client().verify_key()
    assert seen["url"].endswith("/models")
