"""Search issues via the GitHub API."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext
from githubbench_delta.tools.github._helpers import github_client, parse_owner_repo


class SearchIssuesTool(BaseTool):
    """Search repository issues (read-only)."""

    name = "search_issues"
    description = "Search GitHub issues in a repository (requires GITHUB_TOKEN)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords (appended to repo filter)",
            },
            "repository": {
                "type": "string",
                "description": "owner/repo (defaults to task repository_url)",
            },
            "max_results": {"type": "integer", "default": 20},
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        query = arguments.get("query")
        if not query or not isinstance(query, str):
            raise ToolExecutionError("query is required", tool_name=self.name)
        repo_slug = arguments.get("repository") or context.repository_url
        owner, repo_name = parse_owner_repo(repo_slug if isinstance(repo_slug, str) else None)
        max_results = int(arguments.get("max_results") or 20)
        q = f"repo:{owner}/{repo_name} is:issue {query}"
        try:
            gh = github_client(context)
            results = gh.search_issues(q)
        except ToolExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolExecutionError(
                f"Issue search failed: {exc}",
                tool_name=self.name,
            ) from exc
        lines: list[str] = []
        for idx, issue in enumerate(results):
            if idx >= max_results:
                break
            lines.append(f"#{issue.number} [{issue.state}] {issue.title}")
        return "\n".join(lines) if lines else "(no issues found)"
