"""Provider adapter protocol shared by MiniCPM, Claude, and Codex."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.models import ToolCall
from githubbench_delta.core.retry import RetryPolicy
from githubbench_delta.tools.base import ToolSpec


class ChatMessage(BaseModel):
    """Normalized chat message used across providers."""

    role: str
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class ProviderUsage(BaseModel):
    """Token usage returned by a provider call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ProviderResponse(BaseModel):
    """Normalized provider completion result."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    raw: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None


class ProviderAdapter(ABC):
    """Swappable LLM provider adapter. Agents never call SDKs directly."""

    name: str

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_policy = retry_policy or RetryPolicy()

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
    ) -> ProviderResponse:
        """Run one model completion turn with optional tools."""
