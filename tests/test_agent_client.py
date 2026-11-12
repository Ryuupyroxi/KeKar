import asyncio

import httpx
import pytest

from src.agent.client import LLMClient, LLMBusy
from src.config.settings import Settings


def _settings():
    return Settings(api_key="test-key", model_chain=["model-a", "model-b"],
                    request_timeout_s=5)


class _FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {
            "choices": [{"message": {"content": "ok", "tool_calls": []},
                         "finish_reason": "stop"}]}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, url, headers=None, json=None):
        if json["model"] == "model-a":
            return _FakeResponse(500)
        return _FakeResponse(200)


def test_falls_back_on_500(monkeypatch):
    monkeypatch.setattr("src.agent.client.httpx.AsyncClient", _FakeClient)
    resp = asyncio.run(LLMClient(_settings()).chat([{"role": "user", "content": "hi"}]))
    assert resp.content == "ok"
    assert resp.model == "model-b"


def test_raises_when_all_models_fail(monkeypatch):
    class _AllFail(_FakeClient):
        async def post(self, url, headers=None, json=None):
            return _FakeResponse(503)

    monkeypatch.setattr("src.agent.client.httpx.AsyncClient", _AllFail)
    with pytest.raises(LLMBusy):
        asyncio.run(LLMClient(_settings()).chat([{"role": "user", "content": "hi"}]))


def test_quotes_the_provider_reason_in_the_fallback_message(monkeypatch):
    """A bare status code hides why every model failed."""
    class _NoCredits(_FakeClient):
        async def post(self, url, headers=None, json=None):
            return _FakeResponse(429, {"error": {
                "message": "You have no credits remaining."}})

    monkeypatch.setattr("src.agent.client.httpx.AsyncClient", _NoCredits)
    with pytest.raises(LLMBusy) as exc:
        asyncio.run(LLMClient(_settings()).chat(
            [{"role": "user", "content": "hi"}]))
    assert "no credits" in str(exc.value)
