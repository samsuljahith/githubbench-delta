"""OpenAI-compatible chat completions provider (Ollama / MiniCPM)."""

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


class OpenAICompatibleProvider(ProviderAdapter):
    """AsyncOpenAI chat.completions against OpenAI-compatible endpoints."""

    name = "openai_compatible"

    def _client(self):
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key or "ollama",
            base_url=self.base_url,
        )

    def _to_openai_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                item["content"] = msg.content
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            out.append(item)
        return out

    def _to_openai_tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
    ) -> ProviderResponse:
        client = self._client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)

        async def _call() -> Any:
            try:
                return await client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001
                raise self._map_error(exc) from exc

        response = await retry_async(_call, self.retry_policy)
        choice = response.choices[0]
        message = choice.message
        tool_calls: list[ToolCall] = []
        raw_tool_calls: list[dict[str, Any]] = []
        for tc in message.tool_calls or []:
            args: dict[str, Any]
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            call_id = tc.id or new_event_id()
            tool_calls.append(ToolCall(id=call_id, name=tc.function.name, arguments=args))
            raw_tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
            )
        usage = ProviderUsage()
        if response.usage is not None:
            usage = ProviderUsage(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
            )
        return ProviderResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason,
            raw={"tool_calls": raw_tool_calls},
        )

    @staticmethod
    def _map_error(exc: Exception) -> ProviderError:
        name = type(exc).__name__.lower()
        msg = str(exc)
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status == 429 or "rate" in name or "rate_limit" in msg.lower():
            return RateLimitError(msg)
        return ProviderError(msg)
