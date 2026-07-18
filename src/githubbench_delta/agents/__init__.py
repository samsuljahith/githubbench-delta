"""Agent abstractions, providers, and registries."""

from githubbench_delta.agents.base import BaseAgent
from githubbench_delta.agents.claude import ClaudeAgent
from githubbench_delta.agents.codex import CodexAgent
from githubbench_delta.agents.minicpm import MiniCPMAgent
from githubbench_delta.agents.registry import (
    create_agent,
    create_agents_from_app_config,
    list_agent_ids,
    register_agent,
)

__all__ = [
    "BaseAgent",
    "MiniCPMAgent",
    "ClaudeAgent",
    "CodexAgent",
    "create_agent",
    "create_agents_from_app_config",
    "list_agent_ids",
    "register_agent",
]
