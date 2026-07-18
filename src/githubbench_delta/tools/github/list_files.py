"""List files under a local repository path."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext
from githubbench_delta.tools.github._helpers import resolve_under_repo

_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache"}


class ListFilesTool(BaseTool):
    """List files in the local repository (read-only)."""

    name = "list_files"
    description = "List files under a directory in the local repository checkout."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory relative to repo root (default '.')",
                "default": ".",
            },
            "max_entries": {
                "type": "integer",
                "default": 500,
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        repo = context.require_repo_path()
        rel = arguments.get("path") or "."
        if not isinstance(rel, str):
            raise ToolExecutionError("path must be a string", tool_name=self.name)
        root = resolve_under_repo(repo, rel)
        if not root.exists():
            raise ToolExecutionError(f"Path not found: {rel}", tool_name=self.name)
        max_entries = int(arguments.get("max_entries") or 500)
        entries: list[str] = []
        base = root if root.is_dir() else root.parent
        for path in sorted(base.rglob("*")):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.is_file():
                try:
                    rel_path = path.relative_to(repo)
                except ValueError:
                    continue
                entries.append(str(rel_path))
                if len(entries) >= max_entries:
                    break
        return "\n".join(entries) if entries else "(no files)"
