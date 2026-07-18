"""Read a file from a local repository checkout."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext
from githubbench_delta.tools.github._helpers import resolve_under_repo


class ReadFileTool(BaseTool):
    """Read file contents from the local repository path."""

    name = "read_file"
    description = "Read the contents of a file in the local repository checkout."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path relative to the repository root",
            },
            "max_bytes": {
                "type": "integer",
                "description": "Optional max bytes to return",
                "default": 100_000,
            },
        },
        "required": ["path"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        path = arguments.get("path")
        if not path or not isinstance(path, str):
            raise ToolExecutionError("path is required", tool_name=self.name)
        max_bytes = int(arguments.get("max_bytes") or 100_000)
        repo = context.require_repo_path()
        target = resolve_under_repo(repo, path)
        if not target.is_file():
            raise ToolExecutionError(f"File not found: {path}", tool_name=self.name)
        data = target.read_bytes()[:max_bytes]
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
