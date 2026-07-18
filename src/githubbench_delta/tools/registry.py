"""Tool plugin registry."""

from __future__ import annotations

from githubbench_delta.core.errors import RegistryError
from githubbench_delta.tools.base import BaseTool, ToolSpec


class ToolRegistry:
    """Register and resolve tool plugins by name."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise RegistryError("Tool name must be non-empty")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise RegistryError(f"Unknown tool: {name}") from exc

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [self._tools[name].spec() for name in self.list_names()]

    def __len__(self) -> int:
        return len(self._tools)


def create_default_github_registry() -> ToolRegistry:
    """Build a registry with the standard read-only GitHub tools."""

    from githubbench_delta.tools.github.list_files import ListFilesTool
    from githubbench_delta.tools.github.read_commit import ReadCommitTool
    from githubbench_delta.tools.github.read_file import ReadFileTool
    from githubbench_delta.tools.github.read_pull_request import ReadPullRequestTool
    from githubbench_delta.tools.github.repository_metadata import RepositoryMetadataTool
    from githubbench_delta.tools.github.search_issues import SearchIssuesTool
    from githubbench_delta.tools.github.search_repository import SearchRepositoryTool

    registry = ToolRegistry()
    for tool in (
        ReadFileTool(),
        SearchRepositoryTool(),
        ListFilesTool(),
        ReadCommitTool(),
        ReadPullRequestTool(),
        SearchIssuesTool(),
        RepositoryMetadataTool(),
    ):
        registry.register(tool)
    return registry
