"""Tool registry and read-only local tools."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo

from githubbench_delta.core.errors import RegistryError, ToolExecutionError
from githubbench_delta.core.models import ToolCall
from githubbench_delta.tools.base import ToolContext
from githubbench_delta.tools.executor import ToolExecutor
from githubbench_delta.tools.registry import create_default_github_registry


@pytest.fixture
def local_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "hello.py").write_text("print('hello world')\n", encoding="utf-8")
    (repo_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
    repo = Repo.init(repo_dir)
    repo.index.add(["src/hello.py", "README.md"])
    repo.index.commit("initial")
    return repo_dir


def test_default_registry_has_seven_tools() -> None:
    registry = create_default_github_registry()
    names = registry.list_names()
    assert len(names) == 7
    assert "read_file" in names
    assert "search_issues" in names


@pytest.mark.asyncio
async def test_read_list_search_commit_tools(local_repo: Path) -> None:
    registry = create_default_github_registry()
    executor = ToolExecutor(registry)
    ctx = ToolContext(repo_path=local_repo, repository_url="acme/demo")

    read = await executor.execute(
        ToolCall(id="1", name="read_file", arguments={"path": "src/hello.py"}),
        ctx,
    )
    assert read.success
    assert "hello world" in read.output

    listed = await executor.execute(
        ToolCall(id="2", name="list_files", arguments={"path": "."}),
        ctx,
    )
    assert listed.success
    assert "src/hello.py" in listed.output

    search = await executor.execute(
        ToolCall(id="3", name="search_repository", arguments={"query": "hello"}),
        ctx,
    )
    assert search.success
    assert "hello.py" in search.output

    commit = await executor.execute(
        ToolCall(id="4", name="read_commit", arguments={"sha": "HEAD"}),
        ctx,
    )
    assert commit.success
    assert "initial" in commit.output


@pytest.mark.asyncio
async def test_unknown_tool_and_missing_repo() -> None:
    registry = create_default_github_registry()
    executor = ToolExecutor(registry)
    bad = await executor.execute(
        ToolCall(id="x", name="not_a_tool", arguments={}),
        ToolContext(),
    )
    assert not bad.success
    assert "Unknown tool" in (bad.error or "")

    with pytest.raises(ToolExecutionError):
        await registry.get("read_file").execute({"path": "a.py"}, ToolContext())


def test_registry_get_unknown() -> None:
    registry = create_default_github_registry()
    with pytest.raises(RegistryError):
        registry.get("write_file")
