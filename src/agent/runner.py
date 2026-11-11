"""The agent loop: system prompt -> LLM -> tool calls -> LLM -> final answer."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from .client import LLMClient
from .soul import SOUL
from .tools import TOOL_SCHEMAS, ToolContext, dispatch_tool

MAX_HISTORY_TURNS = 12


@dataclass
class AgentResult:
    text: str
    tool_calls: int
    model: str


class AgentCancelled(Exception):
    pass


class AgentStepLimit(Exception):
    pass


class CancelFlag:
    """A thread-safe cancellation signal, checked between agent steps.

    The agent loop runs in a QThread, so the UI cannot touch an asyncio.Event.
    A plain boolean guarded by the GIL is enough: the loop checks it before
    each model call and stops at the next opportunity.
    """

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled


class AgentRunner:
    def __init__(self, client: LLMClient, settings, ctx: ToolContext):
        self.client = client
        self.settings = settings
        self.ctx = ctx

    async def run(self, user_message: str, history: list[dict],
                  cancel: CancelFlag | None = None) -> AgentResult:
        messages: list[dict] = [{"role": "system", "content": SOUL}]
        messages += history[-MAX_HISTORY_TURNS * 2:]
        messages.append({"role": "user", "content": user_message})

        tool_calls = 0
        model_used = ""
        for _ in range(self.settings.max_agent_steps):
            if cancel is not None and cancel.cancelled:
                raise AgentCancelled()
            response = await self.client.chat(messages, tools=TOOL_SCHEMAS)
            model_used = response.model
            if not response.tool_calls:
                return AgentResult(text=response.content,
                                   tool_calls=tool_calls, model=model_used)

            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls,
            })
            for call in response.tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                try:
                    arguments = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = await dispatch_tool(name, arguments, self.ctx)
                tool_calls += 1
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": result,
                })

        raise AgentStepLimit(
            f"the assistant did not finish within {self.settings.max_agent_steps} steps")
