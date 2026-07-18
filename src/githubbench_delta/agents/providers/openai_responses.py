"""OpenAI Responses API provider (Codex)."""

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


class OpenAIResponsesProvider(ProviderAdapter):
    """AsyncOpenAI responses.create with function tools."""

    name = "openai_responses"

    def _client(self):
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return AsyncOpenAI(**kwargs)

    def _to_input(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "tool":
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": msg.tool_call_id or "",
                        "output": msg.content or "",
                    }
                )
                continue
            if msg.role == "assistant" and msg.tool_calls:
                if msg.content:
                    items.append(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": msg.content,
                        }
                    )
                for tc in msg.tool_calls:
                    fn = tc.get("function", {})
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": tc.get("id") or new_event_id(),
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments") or "{}",
                        }
                    )
                continue
            role = msg.role if msg.role in {"user", "assistant", "system"} else "user"
            items.append(
                {
                    "type": "message",
                    "role": role,
                    "content": msg.content or "",
                }
            )
        return items

    def _to_tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
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
            "input": self._to_input(messages),
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = self._to_tools(tools)

        async def _call() -> Any:
            try:
                return await client.responses.create(**kwargs)
            except Exception as exc:  # noqa: BLE001
                raise self._map_error(exc) from exc

        response = await retry_async(_call, self.retry_policy)
        text = getattr(response, "output_text", None) or ""
        tool_calls: list[ToolCall] = []
        raw_tool_calls: list[dict[str, Any]] = []
        for item in getattr(response, "output", None) or []:
            itype = getattr(item, "type", None)
            if itype in {"function_call", "tool_call"}:
                call_id = (
                    getattr(item, "call_id", None) or getattr(item, "id", None) or new_event_id()
                )
                name = getattr(item, "name", "") or ""
                raw_args = getattr(item, "arguments", "{}") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except json.JSONDecodeError:
                    args = {"_raw": raw_args}
                tool_calls.append(ToolCall(id=call_id, name=name, arguments=args))
                args_str = raw_args if isinstance(raw_args, str) else json.dumps(raw_args)
                raw_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": args_str},
                    }
                )
            elif itype == "message" and not text:
                content = getattr(item, "content", None) or []
                parts: list[str] = []
                for part in content:
                    if getattr(part, "type", None) == "output_text":
                        parts.append(getattr(part, "text", "") or "")
                    elif isinstance(part, dict) and part.get("type") == "output_text":
                        parts.append(str(part.get("text", "")))
                if parts:
                    text = "".join(parts)

        usage = ProviderUsage()
        resp_usage = getattr(response, "usage", None)
        if resp_usage is not None:
            usage = ProviderUsage(
                prompt_tokens=getattr(resp_usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(resp_usage, "output_tokens", 0) or 0,
                total_tokens=getattr(resp_usage, "total_tokens", 0) or 0,
            )
            if usage.total_tokens == 0:
                usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

        return ProviderResponse(
            text=text or "",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=getattr(response, "status", None),
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
