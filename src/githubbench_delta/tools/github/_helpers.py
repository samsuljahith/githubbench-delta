"""Shared helpers for GitHub / local-repo tools."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from githubbench_delta.core.errors import ToolExecutionError
from githubbench_delta.tools.base import ToolContext


def resolve_under_repo(repo_path: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``repo_path`` and reject path escape."""

    candidate = (repo_path / relative).resolve()
    root = repo_path.resolve()
    if not str(candidate).startswith(str(root)):
        raise ToolExecutionError(
            f"Path escapes repository root: {relative}",
            tool_name=None,
            fatal=False,
        )
    return candidate


def parse_owner_repo(url: str | None) -> tuple[str, str]:
    """Parse owner/repo from a GitHub URL or owner/repo slug."""

    if not url:
        raise ToolExecutionError("repository_url is required", fatal=False)
    text = url.strip().rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    if re.fullmatch(r"[\w.-]+/[\w.-]+", text):
        owner, repo = text.split("/", 1)
        return owner, repo
    parsed = urlparse(text)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ToolExecutionError(f"Cannot parse owner/repo from {url!r}", fatal=False)
    return parts[0], parts[1]


def github_client(context: ToolContext):
    """Create a PyGithub Github client from context token."""

    from github import Auth, Github

    token = context.require_github_token()
    return Github(auth=Auth.Token(token))
