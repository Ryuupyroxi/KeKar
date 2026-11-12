"""Tests for provider detection, model discovery, and probing."""
import httpx
import pytest

from src.agent import providers


# -- detection -------------------------------------------------------------

def test_detects_openrouter_by_prefix():
    assert [p.id for p in providers.detect("sk-or-v1-abc")] == ["openrouter"]


def test_detects_openai_project_key():
    assert [p.id for p in providers.detect("sk-proj-abc")] == ["openai"]


def test_detects_groq_by_prefix():
    assert [p.id for p in providers.detect("gsk_abc")] == ["groq"]


def test_generic_sk_prefix_is_ambiguous_not_guessed():
    """OpenAI and DeepSeek both use sk-; naming one would send the key wrong."""
    ids = {p.id for p in providers.detect("sk-abcdef")}
    assert "openai" in ids
    assert "deepseek" in ids
    assert providers.best_guess("sk-abcdef") is None


def test_best_guess_returns_the_single_match():
    assert providers.best_guess("sk-or-v1-abc").id == "openrouter"


def test_detect_empty_key_is_no_match():
    assert providers.detect("") == []


def test_unrecognized_google_key_gets_a_useful_hint():
    hint = providers.unrecognized_hint("AIzaSyABC")
    assert "Google" in hint


def test_unrecognized_anthropic_key_gets_a_useful_hint():
    hint = providers.unrecognized_hint("sk-ant-api03-ABC")
    assert "Anthropic" in hint


def test_by_id_finds_a_provider():
    assert providers.by_id("openrouter").name == "OpenRouter"
    assert providers.by_id("nope") is None


# -- model discovery --------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_models_returns_sorted_ids(monkeypatch):
    async def fake_get(self, url, **kw):
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"data": [
            {"id": "zeta/model"}, {"id": "alpha/model"}]})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    ids = await providers.fetch_models("https://example.test/v1", "sk-test")
    assert ids == ["alpha/model", "zeta/model"]


@pytest.mark.asyncio
async def test_fetch_models_sends_the_key_and_endpoint(monkeypatch):
    seen = {}

    async def fake_get(self, url, **kw):
        seen["url"] = url
        seen["headers"] = kw.get("headers") or {}
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"data": []})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    await providers.fetch_models("https://example.test/v1", "sk-test")
    assert seen["url"] == "https://example.test/v1/models"
    assert seen["headers"].get("Authorization") == "Bearer sk-test"


@pytest.mark.asyncio
async def test_fetch_models_requires_an_endpoint():
    with pytest.raises(ValueError):
        await providers.fetch_models("", "sk-test")


# -- probing ----------------------------------------------------------------

def _response(status, url="https://example.test/v1/chat/completions",
              payload=None):
    request = httpx.Request("POST", url)
    return httpx.Response(status, request=request, json=payload or {})


@pytest.mark.asyncio
async def test_probe_reports_success_with_the_model(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await providers.probe("https://example.test/v1", "sk-test",
                                    "test/model")
    assert ok is True
    assert "test/model" in msg


@pytest.mark.asyncio
async def test_probe_quotes_the_provider_error(monkeypatch):
    async def fake_post(self, url, **kw):
        return _response(429, payload={"error": {
            "message": "You have no credits remaining."}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await providers.probe("https://example.test/v1", "sk-test",
                                    "test/model")
    assert ok is False
    assert "no credits" in msg


@pytest.mark.asyncio
async def test_probe_survives_a_network_failure(monkeypatch):
    async def fake_post(self, url, **kw):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    ok, msg = await providers.probe("https://example.test/v1", "sk-test",
                                    "test/model")
    assert ok is False
    assert "Could not reach" in msg


@pytest.mark.asyncio
async def test_probe_needs_a_model():
    ok, msg = await providers.probe("https://example.test/v1", "sk-test", "")
    assert ok is False
    assert "No model" in msg


# -- one-time migration of a default provider ------------------------------

@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    """Point the data directory at a throwaway path."""
    from src import paths
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def test_migrate_switches_a_default_provider_to_match_the_key(temp_data_dir):
    from src.config.settings import Settings

    s = Settings(api_key="sk-proj-abc", provider="openrouter",
                 api_base="https://openrouter.ai/api/v1")
    note = providers.migrate_default_provider(s)

    assert note
    assert s.provider == "openai"
    assert s.api_base == "https://api.openai.com/v1"


def test_migrate_saves_the_change_to_disk(temp_data_dir):
    from src.config.settings import Settings

    providers.migrate_default_provider(Settings(api_key="sk-proj-abc"))

    assert Settings.load().provider == "openai"


def test_migrate_leaves_a_custom_endpoint_alone(temp_data_dir):
    """A non-default endpoint means the user chose deliberately."""
    from src.config.settings import Settings

    s = Settings(api_key="sk-proj-abc", provider="openrouter",
                 api_base="https://my-own-proxy.example/v1")
    assert providers.migrate_default_provider(s) == ""
    assert s.provider == "openrouter"


def test_migrate_leaves_an_explicit_provider_alone(temp_data_dir):
    from src.config.settings import Settings

    s = Settings(api_key="sk-or-v1-abc", provider="openrouter")
    assert providers.migrate_default_provider(s) == ""
    assert s.api_base == "https://openrouter.ai/api/v1"


def test_migrate_ignores_an_empty_key(temp_data_dir):
    from src.config.settings import Settings

    assert providers.migrate_default_provider(Settings()) == ""


def test_migrate_leaves_an_ambiguous_key_alone(temp_data_dir):
    """A generic sk- key could be OpenAI or DeepSeek; do not guess."""
    from src.config.settings import Settings

    s = Settings(api_key="sk-abcdef")
    assert providers.migrate_default_provider(s) == ""
    assert s.provider == "openrouter"

