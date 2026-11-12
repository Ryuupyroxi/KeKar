"""AI provider presets, key detection, and model discovery.

KeKar talks to any OpenAI-compatible endpoint, so the provider is a setting
rather than a build-time constant. The provider is normally detected from the
API key's format and can always be overridden by hand.

Detection is prefix-based and deliberately conservative: it only names a
provider when the key's prefix is unambiguous. Keys it cannot place are left
as "custom" rather than guessed at, because guessing sends the key to the
wrong host.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

USER_AGENT = "KeKar-property-manager"

# The provider a fresh install starts on. Used only to recognise "the user
# never chose a provider", so a deliberate choice is never overridden.
DEFAULT_PROVIDER_ID = "openrouter"


@dataclass(frozen=True)
class Provider:
    """One AI provider preset."""

    id: str
    name: str
    api_base: str
    prefixes: tuple[str, ...] = ()
    default_models: tuple[str, ...] = ()
    notes: str = ""


# Order matters for prefix matching: the most specific prefixes must come
# first, because several providers share the generic "sk-" prefix.
PROVIDERS: tuple[Provider, ...] = (
    Provider(
        id="openrouter",
        name="OpenRouter",
        api_base="https://openrouter.ai/api/v1",
        prefixes=("sk-or-",),
        # "openrouter/free" is OpenRouter's free-models router: it picks
        # whichever free model is available, so it keeps working as the free
        # catalogue changes. The named :free models are fallbacks for when the
        # router itself is rate limited.
        default_models=(
            "openrouter/free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3.5-lightning:free",
            "google/gemma-4-26b-a4b-it:free",
        ),
        notes="Hundreds of models, one key. Free tiers available.",
    ),
    Provider(
        id="openai",
        name="OpenAI",
        api_base="https://api.openai.com/v1",
        prefixes=("sk-proj-", "sk-svcacct-", "sk-"),
        default_models=(
            "gpt-4o-mini",
            "gpt-4.1-mini",
            "gpt-5-mini",
        ),
        notes="Project keys (sk-proj-…) and service accounts.",
    ),
    Provider(
        id="groq",
        name="Groq",
        api_base="https://api.groq.com/openai/v1",
        prefixes=("gsk_",),
        default_models=("llama-3.3-70b-versatile",),
        notes="Very fast inference, generous free tier.",
    ),
    Provider(
        id="cerebras",
        name="Cerebras Cloud",
        api_base="https://api.cerebras.ai/v1",
        prefixes=("csk-",),
        default_models=("llama-3.3-70b",),
        notes="Fast GPU inference.",
    ),
    Provider(
        id="xai",
        name="xAI (Grok)",
        api_base="https://api.x.ai/v1",
        prefixes=("xai-",),
        default_models=("grok-3-mini", "grok-3"),
    ),
    Provider(
        id="deepseek",
        name="DeepSeek",
        api_base="https://api.deepseek.com/v1",
        prefixes=("sk-",),
        default_models=("deepseek-chat", "deepseek-reasoner"),
        notes="Shares the generic sk- prefix with OpenAI; probing decides.",
    ),
    Provider(
        id="mistral",
        name="Mistral",
        api_base="https://api.mistral.ai/v1",
        prefixes=("mistral_",),
        default_models=("mistral-small-latest", "magistral-small-latest"),
    ),
    Provider(
        id="nous",
        name="Nous Portal",
        api_base="https://inference-api.nousresearch.com/v1",
        prefixes=(),
        default_models=("nousresearch/hermes-4-405b",),
    ),
    Provider(
        id="custom",
        name="Custom / other",
        api_base="",
        prefixes=(),
        notes="Any OpenAI-compatible endpoint.",
    ),
)

# Providers whose chat API is not OpenAI-compatible. KeKar can list their
# models but cannot call them through the standard chat endpoint.
NON_OPENAI = {
    "google": ("Google AI Studio", "https://generativelanguage.googleapis.com/v1beta",
               "Uses :generateContent, not /chat/completions. Point KeKar at "
               "an OpenAI-compatible proxy for this provider."),
    "anthropic": ("Anthropic", "https://api.anthropic.com/v1",
                  "Needs an x-api-key header and anthropic-version. Point "
                  "KeKar at an OpenAI-compatible proxy for this provider."),
}


def by_id(provider_id: str) -> Provider | None:
    for provider in PROVIDERS:
        if provider.id == provider_id:
            return provider
    return None


def detect(key: str) -> list[Provider]:
    """Providers whose key format matches ``key``.

    When a key matches prefixes of different lengths, only the longest match
    counts: ``sk-proj-…`` must resolve to OpenAI even though it also starts
    with DeepSeek's generic ``sk-``.

    Returns every provider tied at that longest length, because a generic
    prefix can genuinely mean more than one provider. The caller decides
    whether to probe them.
    """
    if not key:
        return []
    scored: list[tuple[int, Provider]] = []
    for provider in PROVIDERS:
        for prefix in provider.prefixes:
            if key.startswith(prefix):
                scored.append((len(prefix), provider))
                break
    if not scored:
        return []
    longest = max(length for length, _ in scored)
    matches: list[Provider] = []
    for length, provider in scored:
        if length == longest and all(provider.id != m.id for m in matches):
            matches.append(provider)
    return matches


def best_guess(key: str) -> Provider | None:
    """The single provider an unambiguous key belongs to, else None.

    Used where a network probe is not possible — the first-run wizard, which
    has to fill in an endpoint before it can verify anything.
    """
    matches = detect(key)
    return matches[0] if len(matches) == 1 else None


def migrate_default_provider(settings) -> str:
    """Point settings at the provider the key actually belongs to.

    Only acts while the stored provider is still the built-in default, so a
    deliberate provider choice is never overridden. Without this, a key added
    through the wizard before provider detection existed is left pointing at
    the wrong host forever.

    Returns a human-readable note when something changed, else "".
    """
    if not settings.api_key:
        return ""
    matches = detect(settings.api_key)
    if len(matches) != 1:
        return ""
    prov = matches[0]
    default = by_id(DEFAULT_PROVIDER_ID)
    untouched_default = (
        default is not None
        and settings.provider == default.id
        and settings.api_base == default.api_base)
    if untouched_default and prov.id != settings.provider:
        settings.provider = prov.id
        if prov.api_base:
            settings.api_base = prov.api_base
        if prov.default_models:
            settings.model_chain = list(prov.default_models)
        try:
            settings.save()
        except Exception:
            return ""
        return (f"Detected a {prov.name} key, so the assistant was switched "
                f"to {prov.name}.")
    return ""


def unrecognized_hint(key: str) -> str:
    """A human explanation for a key whose provider is unknown."""
    if key.startswith("AIza"):
        name, base, note = NON_OPENAI["google"]
        return f"That looks like a {name} key. {note}"
    if key.startswith("sk-ant-"):
        name, base, note = NON_OPENAI["anthropic"]
        return f"That looks like an {name} key. {note}"
    return ("KeKar does not recognise that key's provider. Choose 'Custom / "
            "other' and enter the endpoint yourself.")


async def fetch_models(api_base: str, api_key: str,
                       timeout: float = 25.0) -> list[str]:
    """List model ids from an OpenAI-compatible ``/models`` endpoint.

    Returns ids sorted by name. Raises ``httpx.HTTPError`` on network
    failure and ``ValueError`` when the response is not a model list — the
    caller is expected to show that to the user.
    """
    if not api_base:
        raise ValueError("No endpoint is set.")
    url = f"{api_base.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
    return sorted(ids)


async def probe(api_base: str, api_key: str, model: str,
                timeout: float = 30.0) -> tuple[bool, str]:
    """One minimal completion: the only real test of key + endpoint + model.

    Returns ``(ok, message)``. The message quotes the provider's own error
    text when it gives one, because "no credits remaining" and "bad key"
    look identical from the status code alone.
    """
    if not api_key:
        return False, "No API key is set."
    if not api_base:
        return False, "No endpoint is set."
    if not model:
        return False, "No model is configured."
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json",
               "User-Agent": USER_AGENT}
    payload = {"model": model,
               "messages": [{"role": "user", "content": "hi"}],
               "max_tokens": 1}
    try:
        async with httpx.AsyncClient(timeout=timeout) as http:
            resp = await http.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return False, (f"Could not reach {api_base} ({type(exc).__name__}). "
                       f"Check the endpoint and the internet connection.")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except Exception:
            detail = ""
        detail = " ".join(detail.split())
        if resp.status_code in (401, 403):
            text = "The key was rejected."
        elif resp.status_code == 429:
            text = "The provider refused the request (HTTP 429)."
        else:
            text = f"The provider returned HTTP {resp.status_code}."
        if detail:
            text += f" {detail[:200]}"
        return False, text

    return True, f"Connected via {model}."
