"""Provider adapter translation tests (mocked SDKs)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from githubbench_delta.agents.providers.anthropic import AnthropicProvider
from githubbench_delta.agents.providers.base import ChatMessage
from githubbench_delta.agents.providers.openai_compatible import OpenAICompatibleProvider
from githubbench_delta.agents.providers.openai_responses import OpenAIResponsesProvider
from githubbench_delta.core.retry import RetryPolicy
from githubbench_delta.tools.base import ToolSpec

TOOL = ToolSpec(
    name="read_file",
    description="Read a file",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)


@pytest.mark.asyncio
async def test_openai_compatible_parses_tool_calls() -> None:
    provider = OpenAICompatibleProvider(
        model="minicpm",
        api_key="ollama",
        base_url="http://localhost:11434/v1",
        retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0, jitter=False),
    )
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="read_file", arguments='{"path":"a.py"}'),
    )
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    response = SimpleNamespace(choices=[choice], usage=usage)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=response)

    with patch.object(provider, "_client", return_value=mock_client):
        result = await provider.complete(
            [ChatMessage(role="user", content="read a.py")],
            [TOOL],
        )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments["path"] == "a.py"
    assert result.usage.total_tokens == 15
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_anthropic_parses_tool_use() -> None:
    provider = AnthropicProvider(
        model="claude-test",
        api_key="sk-test",
        retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0, jitter=False),
    )
    blocks = [
        SimpleNamespace(type="text", text="Looking"),
        SimpleNamespace(type="tool_use", id="tu1", name="read_file", input={"path": "b.py"}),
    ]
    response = SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=3, output_tokens=4),
        stop_reason="tool_use",
    )
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    with patch.object(provider, "_client", return_value=mock_client):
        result = await provider.complete(
            [
                ChatMessage(role="system", content="sys"),
                ChatMessage(role="user", content="hi"),
            ],
            [TOOL],
        )

    assert "Looking" in result.text
    assert result.tool_calls[0].arguments["path"] == "b.py"
    assert result.usage.prompt_tokens == 3


@pytest.mark.asyncio
async def test_openai_responses_parses_function_call() -> None:
    provider = OpenAIResponsesProvider(
        model="gpt-test",
        api_key="sk-test",
        retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0, jitter=False),
    )
    item = SimpleNamespace(
        type="function_call",
        call_id="fc1",
        name="read_file",
        arguments='{"path":"c.py"}',
    )
    response = SimpleNamespace(
        output_text="",
        output=[item],
        usage=SimpleNamespace(input_tokens=2, output_tokens=2, total_tokens=4),
        status="completed",
    )
    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(return_value=response)

    with patch.object(provider, "_client", return_value=mock_client):
        result = await provider.complete(
            [ChatMessage(role="user", content="c")],
            [TOOL],
        )

    assert result.tool_calls[0].id == "fc1"
    assert result.tool_calls[0].arguments["path"] == "c.py"
