"""Anthropic Messages API provider (Claude)."""

from __future__ import annotations

import json
from typing import Any

from githubbench_delta.agents.providers.base import (
    ChatMessage,
    ProviderAdapter,
    ProviderResponse,
    ProviderUsage,
)
from githubbench_delta.core.errors import ProviderError, RateLimitError
from githubbench_delta.core.models import ToolCall
from githubbench_delta.core.retry import retry_async
from githubbench_delta.observability.ids import new_event_id
from githubbench_delta.tools.base import ToolSpec


class AnthropicProvider(ProviderAdapter):
    """AsyncAnthropic messages.create with tool use."""

    name = "anthropic"

    def _client(self):
        from anthropic import AsyncAnthropic

        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return AsyncAnthropic(**kwargs)

    def _split_system(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                if msg.content:
                    system_parts.append(msg.content)
                continue
            if msg.role == "tool":
                api_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.tool_call_id or "",
                                "content": msg.content or "",
                            }
                        ],
                    }
                )
                continue
            if msg.role == "assistant" and msg.tool_calls:
                content: list[dict[str, Any]] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    fn = tc.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("id") or new_event_id(),
                            "name": fn.get("name", ""),
                            "input": args,
                        }
                    )
                api_messages.append({"role": "assistant", "content": content})
                continue
            api_messages.append({"role": msg.role, "content": msg.content or ""})
        system = "\n\n".join(system_parts) if system_parts else None
        return system, api_messages

    def _to_anthropic_tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
    ) -> ProviderResponse:
        client = self._client()
        system, api_messages = self._split_system(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        async def _call() -> Any:
            try:
                return await client.messages.create(**kwargs)
            except Exception as exc:  # noqa: BLE001
                raise self._map_error(exc) from exc

        response = await retry_async(_call, self.retry_policy)
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        raw_tool_calls: list[dict[str, Any]] = []
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", "") or "")
            elif btype == "tool_use":
                call_id = getattr(block, "id", None) or new_event_id()
                name = getattr(block, "name", "")
                inp = dict(getattr(block, "input", {}) or {})
                tool_calls.append(ToolCall(id=call_id, name=name, arguments=inp))
                raw_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(inp),
                        },
                    }
                )
        usage = ProviderUsage(
            prompt_tokens=getattr(response.usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(response.usage, "output_tokens", 0) or 0,
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=getattr(response, "stop_reason", None),
            raw={"tool_calls": raw_tool_calls},
        )

    @staticmethod
    def _map_error(exc: Exception) -> ProviderError:
        name = type(exc).__name__.lower()
        msg = str(exc)
        status = getattr(exc, "status_code", None)
        if status == 429 or "rate" in name or "rate_limit" in msg.lower():
            return RateLimitError(msg)
        return ProviderError(msg)
