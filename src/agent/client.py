"""Minimal OpenAI-compatible chat client with a model fallback chain."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

from ..config.settings import Settings

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

    async def verify_key(self) -> tuple[bool, str]:
        """Check the key against the provider without spending a completion.

        Returns (ok, message). Never raises: a network problem is a normal
        outcome here, not an exception.
        """
        if not self.settings.api_key:
            return False, "No API key is set."
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        url = f"{self.settings.api_base.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(url, headers=headers)
        except httpx.HTTPError as exc:
            return False, (f"Could not reach {self.settings.api_base} "
                           f"({type(exc).__name__}). Check the internet "
                           f"connection and try again.")
        if resp.status_code in (401, 403):
            return False, "That key was rejected. Please check it and try again."
        if resp.status_code >= 400:
            return False, f"The service returned an error (HTTP {resp.status_code})."
        return True, "Connected."

    def summarize(self, text: str) -> str:
        """Synchronous convenience wrapper (used by memory condensing)."""
        return asyncio.run(self.complete(text))
