"""Search file contents in a local repository checkout."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext

_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache"}
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".rst",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".css",
    ".html",
    ".sh",
}


class SearchRepositoryTool(BaseTool):
    """Case-insensitive content search across text files in the local repo."""

    name = "search_repository"
    description = "Search for a query string in local repository file contents (read-only)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Substring to search for"},
            "max_matches": {"type": "integer", "default": 50},
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        query = arguments.get("query")
        if not query or not isinstance(query, str):
            raise ToolExecutionError("query is required", tool_name=self.name)
        max_matches = int(arguments.get("max_matches") or 50)
        repo = context.require_repo_path()
        needle = query.lower()
        hits: list[str] = []
        for path in repo.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES and path.suffix != "":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    rel = path.relative_to(repo)
                    hits.append(f"{rel}:{lineno}: {line.strip()}")
                    if len(hits) >= max_matches:
                        return "\n".join(hits)
        return "\n".join(hits) if hits else "(no matches)"
