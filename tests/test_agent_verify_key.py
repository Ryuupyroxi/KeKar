"""Tests for LLMClient.verify_key — the first-run connection check.

verify_key used to call GET /models, which several providers serve publicly,
so it reported "Connected" for a key the chat endpoint then rejected. It now
makes a one-token completion instead, which is the only real test.
"""
import httpx
import pytest

from src.agent.client import LLMClient
from src.config.settings import Settings


def _client(key="sk-test-key", models=None):
    return LLMClient(Settings(api_key=key,
                              model_chain=models if models is not None
                              else ["test/model"]))


def _response(status, url="https://example.test/v1/chat/completions",
              method="POST", payload=None):
    request = httpx.Request(method, url)
    return httpx.Response(status, request=request, json=payload or {})


@pytest.mark.asyncio
async def test_verify_key_accepts_200(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client().verify_key()
    assert ok is True
    assert "test/model" in msg


@pytest.mark.asyncio
async def test_verify_key_rejects_401(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(401)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "rejected" in msg


@pytest.mark.asyncio
async def test_verify_key_rejects_403(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(403)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, _ = await _client().verify_key()
    assert ok is False


@pytest.mark.asyncio
async def test_verify_key_survives_network_failure(monkeypatch):
    async def fake_post(self, url, **kw):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "Could not reach" in msg


@pytest.mark.asyncio
async def test_verify_key_reports_server_error(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(503)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "503" in msg


@pytest.mark.asyncio
async def test_verify_key_without_a_key_short_circuits(monkeypatch):
    called = []

    async def fake_post(self, url, **kw):
        called.append(True)
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client(key="").verify_key()
    assert ok is False
    assert "No API key" in msg
    assert called == []


@pytest.mark.asyncio
async def test_verify_key_reports_429_with_the_provider_detail(monkeypatch):
    """A bare "429" hides the real reason; quote the provider's own words."""

    async def fake_post(self, url, **kw):
        return _response(429, payload={"error": {
            "message": "You have no credits remaining."}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client().verify_key()
    assert ok is False
    assert "429" in msg
    assert "no credits" in msg


@pytest.mark.asyncio
async def test_verify_key_without_models_short_circuits(monkeypatch):
    called = []

    async def fake_post(self, url, **kw):
        called.append(True)
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await _client(models=[]).verify_key()
    assert ok is False
    assert "No models" in msg
    assert called == []


@pytest.mark.asyncio
async def test_verify_key_sends_the_authorization_header(monkeypatch):
    seen = {}

    async def fake_post(self, url, **kw):
        seen.update(kw.get("headers") or {})
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await _client("sk-secret-key").verify_key()
    assert seen.get("Authorization") == "Bearer sk-secret-key"


@pytest.mark.asyncio
async def test_verify_key_posts_a_real_completion_request(monkeypatch):
    seen = {}

    async def fake_post(self, url, **kw):
        seen["url"] = url
        seen["json"] = kw.get("json") or {}
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await _client("sk-secret-key", models=["alpha/one", "beta/two"]).verify_key()
    assert seen["url"].endswith("/chat/completions")
    assert seen["json"].get("model") == "alpha/one"
