"""Pluggable tool interface for agent tool use."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """JSON-schema style tool description exposed to providers."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass
class ToolContext:
    """Runtime context available to tools during execution."""

    repo_path: Path | None = None
    repository_url: str | None = None
    repository_ref: str | None = None
    github_token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def require_repo_path(self) -> Path:
        if self.repo_path is None or not self.repo_path.exists():
            from githubbench_delta.core.errors import ToolExecutionError

            raise ToolExecutionError(
                "Tool requires a local repository path (repo_path)",
                fatal=False,
            )
        return self.repo_path

    def require_github_token(self) -> str:
        if not self.github_token:
            from githubbench_delta.core.errors import ToolExecutionError

            raise ToolExecutionError(
                "Tool requires GITHUB_TOKEN / github_token in ToolContext",
                fatal=False,
            )
        return self.github_token


class BaseTool(ABC):
    """Independent tool plugin. Register with ToolRegistry; zero pipeline changes."""

    name: str
    description: str
    parameters: dict[str, Any]

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        """Run the tool and return a string payload for the model."""
