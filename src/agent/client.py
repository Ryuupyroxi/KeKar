"""Minimal OpenAI-compatible chat client with a model fallback chain."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

from ..config.settings import Settings
from . import providers

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    model: str = ""
    finish_reason: str = ""


class LLMBusy(Exception):
    """Raised when every model in the chain failed."""


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def chat(self, messages: list[dict],
                   tools: list[dict] | None = None) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.api_base.rstrip('/')}/chat/completions"
        last_error = "no models configured"

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_s) as http:
            for model in self.settings.model_chain:
                payload: dict = {"model": model, "messages": messages}
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                try:
                    resp = await http.post(url, headers=headers, json=payload)
                except httpx.HTTPError as exc:
                    last_error = f"{model}: {type(exc).__name__}"
                    continue
                if resp.status_code >= 400:
                    # Quote the provider's own reason: "no credits remaining"
                    # and "rate limited" share a status code.
                    try:
                        detail = resp.json().get("error", {}).get(
                            "message", "")
                    except Exception:
                        detail = ""
                    detail = " ".join(detail.split())
                    if detail:
                        last_error = (f"{model}: HTTP {resp.status_code} — "
                                      f"{detail[:200]}")
                    else:
                        last_error = f"{model}: HTTP {resp.status_code}"
                    continue
                try:
                    data = resp.json()
                    message = data["choices"][0]["message"]
                    return LLMResponse(
                        content=message.get("content") or "",
                        tool_calls=message.get("tool_calls") or [],
                        model=model,
                        finish_reason=data["choices"][0].get("finish_reason", ""),
                    )
                except (KeyError, ValueError, IndexError):
                    last_error = f"{model}: malformed response"
                    continue

        raise LLMBusy(f"All models failed. Last error: {last_error}")

    async def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return (await self.chat(messages)).content

    async def list_models(self) -> list[str]:
        """Ask the configured provider which models it offers.

        Raises httpx.HTTPError on a network failure and ValueError when the
        response is not a model list; the caller shows that to the user.
        """
        return await providers.fetch_models(self.settings.api_base,
                                            self.settings.api_key)

    async def verify_key(self) -> tuple[bool, str]:
        """Really check the setup with one minimal completion.

        A ``GET /models`` call is not a verification: on several providers
        that endpoint is public and answers 200 for any key, so it reported
        "Connected" for a key the chat endpoint then rejected. This makes a
        one-token completion through the first model in the chain instead,
        and quotes the provider's own error when it refuses.
        """
        if not self.settings.api_key:
            return False, "No API key is set."
        if not self.settings.model_chain:
            return False, ("No models are configured. Add at least one model "
                           "(or fetch the provider's model list).")
        return await providers.probe(self.settings.api_base,
                                     self.settings.api_key,
                                     self.settings.model_chain[0])

    def summarize(self, text: str) -> str:
        """Synchronous convenience wrapper (used by memory condensing)."""
        return asyncio.run(self.complete(text))
