"""Agent plugin registry."""

from __future__ import annotations

from githubbench_delta.agents.base import BaseAgent
from githubbench_delta.agents.claude import ClaudeAgent
from githubbench_delta.agents.codex import CodexAgent
from githubbench_delta.agents.minicpm import MiniCPMAgent
from githubbench_delta.core.config import AgentProviderConfig, AppConfig, RetryConfig
from githubbench_delta.core.errors import RegistryError
from githubbench_delta.core.models import AgentId
from githubbench_delta.storage.events import create_event_store
from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.tools.registry import ToolRegistry

_AGENT_FACTORIES: dict[AgentId, type[BaseAgent]] = {
    AgentId.MINICPM: MiniCPMAgent,
    AgentId.CLAUDE: ClaudeAgent,
    AgentId.CODEX: CodexAgent,
}


def register_agent(agent_id: AgentId, factory: type[BaseAgent]) -> None:
    """Register or replace an agent class for plugin extensibility."""

    _AGENT_FACTORIES[agent_id] = factory


def list_agent_ids() -> list[AgentId]:
    """Return registered agent ids in stable order."""

    return [aid for aid in AgentId if aid in _AGENT_FACTORIES]


def create_agent(
    config: AgentProviderConfig,
    *,
    tool_registry: ToolRegistry | None = None,
    event_store: EventStore | None = None,
    retry_config: RetryConfig | None = None,
    max_tool_calls: int = 50,
    github_token: str | None = None,
) -> BaseAgent:
    """Instantiate an agent from provider config."""

    cls = _AGENT_FACTORIES.get(config.id)
    if cls is None:
        raise RegistryError(f"No agent factory registered for {config.id}")
    return cls(
        config,
        tool_registry=tool_registry,
        event_store=event_store,
        retry_config=retry_config,
        max_tool_calls=max_tool_calls,
        github_token=github_token,
    )


def create_agents_from_app_config(app_config: AppConfig) -> dict[AgentId, BaseAgent]:
    """Create all enabled agents defined in application config."""

    store = create_event_store(app_config.runtime.event_store)
    agents: dict[AgentId, BaseAgent] = {}
    for cfg in app_config.agents.values():
        if not cfg.enabled:
            continue
        agents[cfg.id] = create_agent(
            cfg,
            event_store=store,
            retry_config=app_config.runtime.retry,
            max_tool_calls=app_config.runtime.max_tool_calls,
            github_token=app_config.env.github_token,
        )
    return agents
