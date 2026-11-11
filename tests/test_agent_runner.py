import asyncio
import json

import pytest

from src.agent.client import LLMResponse
from src.agent.runner import AgentCancelled, AgentRunner, CancelFlag
from src.agent.tools import ToolContext
from src.config.settings import Settings
from src.data.property_repo import PropertyRepo


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def chat(self, messages, tools=None):
        self.calls += 1
        return self.responses.pop(0)


def _ctx(db):
    return ToolContext(db=db, property_repo=PropertyRepo(db.conn),
                       applicant_repo=None, memory=None, settings=None)


def _resp(content="", tool_calls=None):
    return LLMResponse(content=content, tool_calls=tool_calls or [],
                       model="fake", finish_reason="stop")


def test_returns_final_text(db):
    client = FakeClient([_resp(content="hello there")])
    result = asyncio.run(AgentRunner(client, Settings(), _ctx(db)).run("hi", []))
    assert result.text == "hello there"
    assert result.tool_calls == 0


def test_executes_tool_then_answers(db):
    tool_call = {"id": "call_1", "type": "function",
                 "function": {"name": "property_upsert",
                              "arguments": json.dumps(
                                  {"address": "9 Loop Ln", "rent_price": 600})}}
    client = FakeClient([LLMResponse(content="", tool_calls=[tool_call],
                                     model="fake", finish_reason="tool_calls"),
                          _resp(content="Done — I added it.")])
    result = asyncio.run(AgentRunner(client, Settings(), _ctx(db))
                        .run("add a property", []))
    assert result.text == "Done — I added it."
    assert result.tool_calls == 1
    assert len(_ctx(db).property_repo.list()) == 1


def test_cancellation(db):
    client = FakeClient([_resp(content="x")])
    cancel = CancelFlag()
    cancel.cancel()
    with pytest.raises(AgentCancelled):
        asyncio.run(AgentRunner(client, Settings(), _ctx(db))
                    .run("hi", [], cancel=cancel))


def test_cancellation_mid_loop(db):
    """A cancel raised between steps stops the loop before the next call."""
    tool_call = {"id": "c", "type": "function",
                 "function": {"name": "property_list", "arguments": "{}"}}
    client = FakeClient([LLMResponse(content="", tool_calls=[tool_call],
                                      model="fake", finish_reason="tool_calls")]
                        * 5)
    cancel = CancelFlag()

    original_chat = client.chat

    async def chat_and_cancel(messages, tools=None):
        cancel.cancel()
        return await original_chat(messages, tools)

    client.chat = chat_and_cancel
    with pytest.raises(AgentCancelled):
        asyncio.run(AgentRunner(client, Settings(), _ctx(db))
                    .run("loop", [], cancel=cancel))


def test_step_limit(db):
    tool_call = {"id": "c", "type": "function",
                 "function": {"name": "property_list", "arguments": "{}"}}
    looping = FakeClient([LLMResponse(content="", tool_calls=[tool_call],
                                      model="fake", finish_reason="tool_calls")] * 20)
    settings = Settings(max_agent_steps=2)
    with pytest.raises(Exception):
        asyncio.run(AgentRunner(looping, settings, _ctx(db)).run("loop", []))
