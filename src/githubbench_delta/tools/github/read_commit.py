"""Read commit metadata/message from a local git repository."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import BaseTool, ToolContext


class ReadCommitTool(BaseTool):
    """Read a git commit via GitPython (local clone)."""

    name = "read_commit"
    description = "Read commit message and metadata from the local git repository."
    parameters = {
        "type": "object",
        "properties": {
            "sha": {
                "type": "string",
                "description": "Commit SHA or ref (default HEAD)",
                "default": "HEAD",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        from git import InvalidGitRepositoryError, Repo
        from git.exc import BadName

        repo_path = context.require_repo_path()
        sha = arguments.get("sha") or "HEAD"
        if not isinstance(sha, str):
            raise ToolExecutionError("sha must be a string", tool_name=self.name)
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError as exc:
            raise ToolExecutionError(
                f"Not a git repository: {repo_path}",
                tool_name=self.name,
            ) from exc
        try:
            commit = repo.commit(sha)
        except (BadName, ValueError, Exception) as exc:
            raise ToolExecutionError(
                f"Cannot resolve commit {sha!r}: {exc}",
                tool_name=self.name,
            ) from exc
        files = list(commit.stats.files.keys())[:50]
        return (
            f"sha: {commit.hexsha}\n"
            f"author: {commit.author.name} <{commit.author.email}>\n"
            f"date: {commit.committed_datetime.isoformat()}\n"
            f"message:\n{str(commit.message).strip()}\n"
            f"files ({len(commit.stats.files)}):\n" + "\n".join(f"- {f}" for f in files)
        )
