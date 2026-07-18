"""Fetch repository metadata via the GitHub API."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext
from githubbench_delta.tools.github._helpers import github_client, parse_owner_repo


class RepositoryMetadataTool(BaseTool):
    """Read repository metadata (stars, description, default branch, etc.)."""

    name = "repository_metadata"
    description = "Fetch GitHub repository metadata (requires GITHUB_TOKEN)."
    parameters = {
        "type": "object",
        "properties": {
            "repository": {
                "type": "string",
                "description": "owner/repo (defaults to task repository_url)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        repo_slug = arguments.get("repository") or context.repository_url
        owner, repo_name = parse_owner_repo(repo_slug if isinstance(repo_slug, str) else None)
        try:
            gh = github_client(context)
            repo = gh.get_repo(f"{owner}/{repo_name}")
        except ToolExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolExecutionError(
                f"Failed to fetch repository metadata: {exc}",
                tool_name=self.name,
            ) from exc
        return (
            f"full_name: {repo.full_name}\n"
            f"description: {repo.description or ''}\n"
            f"default_branch: {repo.default_branch}\n"
            f"language: {repo.language or ''}\n"
            f"stars: {repo.stargazers_count}\n"
            f"forks: {repo.forks_count}\n"
            f"open_issues: {repo.open_issues_count}\n"
            f"private: {repo.private}\n"
            f"html_url: {repo.html_url}"
        )
