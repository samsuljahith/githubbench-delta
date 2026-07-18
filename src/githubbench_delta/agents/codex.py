"""OpenAI Codex agent via Responses API."""

from __future__ import annotations

import os

from githubbench_delta.agents.base import BaseAgent
from githubbench_delta.agents.providers.openai_responses import OpenAIResponsesProvider
from githubbench_delta.core.config import AgentProviderConfig, RetryConfig
from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.tools.registry import ToolRegistry


class CodexAgent(BaseAgent):
    """Hosted Codex / OpenAI coding agent via the Responses API."""

    def __init__(
        self,
        config: AgentProviderConfig,
        *,
        tool_registry: ToolRegistry | None = None,
        event_store: EventStore | None = None,
        retry_config: RetryConfig | None = None,
        max_tool_calls: int = 50,
        github_token: str | None = None,
        api_key: str | None = None,
    ) -> None:
        key = api_key or os.environ.get(config.api_key_env or "OPENAI_API_KEY")
        provider = OpenAIResponsesProvider(
            model=config.model,
            api_key=key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        super().__init__(
            config,
            provider=provider,
            tool_registry=tool_registry,
            event_store=event_store,
            retry_config=retry_config,
            max_tool_calls=max_tool_calls,
            github_token=github_token,
        )
        self.provider.retry_policy = self.retry_policy()
