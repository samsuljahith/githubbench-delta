"""Read a pull request via the GitHub API (PyGithub)."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext
from githubbench_delta.tools.github._helpers import github_client, parse_owner_repo


class ReadPullRequestTool(BaseTool):
    """Fetch pull request details (read-only)."""

    name = "read_pull_request"
    description = "Read a GitHub pull request by number (requires GITHUB_TOKEN)."
    parameters = {
        "type": "object",
        "properties": {
            "number": {"type": "integer", "description": "Pull request number"},
            "repository": {
                "type": "string",
                "description": "owner/repo (defaults to task repository_url)",
            },
        },
        "required": ["number"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        number = arguments.get("number")
        if number is None:
            raise ToolExecutionError("number is required", tool_name=self.name)
        repo_slug = arguments.get("repository") or context.repository_url
        owner, repo_name = parse_owner_repo(repo_slug if isinstance(repo_slug, str) else None)
        try:
            gh = github_client(context)
            pr = gh.get_repo(f"{owner}/{repo_name}").get_pull(int(number))
        except ToolExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolExecutionError(
                f"Failed to read PR #{number}: {exc}",
                tool_name=self.name,
            ) from exc
        return (
            f"#{pr.number} {pr.title}\n"
            f"state: {pr.state}\n"
            f"user: {pr.user.login if pr.user else ''}\n"
            f"base: {pr.base.ref} <- head: {pr.head.ref}\n"
            f"body:\n{(pr.body or '').strip()}"
        )
