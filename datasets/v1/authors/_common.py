"""Shared helpers for curated v1 corpus task records."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "datasets" / "fixtures"

REPOS: dict[str, dict[str, str]] = {
    "py_cli": {
        "url": "https://github.com/example/widgetcli",
        "local_path": "datasets/fixtures/py_cli",
        "language": "python",
        "branch": "master",
    },
    "py_rag": {
        "url": "https://github.com/example/docsearch-rag",
        "local_path": "datasets/fixtures/py_rag",
        "language": "python",
        "branch": "master",
    },
    "ts_frontend": {
        "url": "https://github.com/example/pulseboard",
        "local_path": "datasets/fixtures/ts_frontend",
        "language": "typescript",
        "branch": "master",
    },
    "go_rest_api": {
        "url": "https://github.com/example/inventoryapi",
        "local_path": "datasets/fixtures/go_rest_api",
        "language": "go",
        "branch": "master",
    },
    "rust_service": {
        "url": "https://github.com/example/notifyrs",
        "local_path": "datasets/fixtures/rust_service",
        "language": "rust",
        "branch": "master",
    },
    "java_backend": {
        "url": "https://github.com/example/billing-backend",
        "local_path": "datasets/fixtures/java_backend",
        "language": "java",
        "branch": "master",
    },
}

DEFAULT_PROMPTS = [
    "system.default",
    "developer.default",
    "task.generic",
    "tool.readonly",
]


def git_sha(fixture: str, rev: str = "HEAD") -> str:
    path = FIXTURES / fixture
    out = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", rev],
        text=True,
    ).strip()
    return out


def git_sha_n(fixture: str, n: int = 1) -> str:
    """Return the nth commit from HEAD (1 = HEAD, 2 = HEAD~1, ...)."""

    rev = "HEAD" if n <= 1 else f"HEAD~{n - 1}"
    return git_sha(fixture, rev)


def repo_ref(fixture: str, *, commit: str | None = None) -> dict[str, Any]:
    meta = REPOS[fixture]
    return {
        "url": meta["url"],
        "local_path": meta["local_path"],
        "branch": meta["branch"],
        "commit_sha": commit or git_sha(fixture),
    }


def tools(*steps: tuple[str, dict[str, Any]] | str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        if isinstance(step, str):
            out.append({"name": step, "arguments": {}, "optional": False})
        else:
            name, args = step
            optional = bool(args.pop("_optional", False))
            desc = str(args.pop("_description", ""))
            out.append(
                {
                    "name": name,
                    "arguments": args,
                    "optional": optional,
                    "description": desc,
                }
            )
    return out


def failures(*items: tuple[str, str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kind, description, metrics in items:
        out.append(
            {
                "kind": kind,
                "description": description,
                "example": description,
                "related_metrics": metrics,
            }
        )
    return out


def task(
    *,
    id: str,
    category: str,
    title: str,
    description: str,
    prompt: str,
    fixture: str,
    difficulty: str,
    difficulty_score: int,
    files: list[str],
    gold: dict[str, Any],
    expected_tool_calls: list[dict[str, Any]],
    failure_examples: list[dict[str, Any]],
    tags: list[str] | None = None,
    alternate_gold_answers: list[dict[str, Any]] | None = None,
    estimated_duration: float = 180.0,
    expected_output: dict[str, Any] | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    meta = REPOS[fixture]
    language = meta["language"]
    repository = repo_ref(fixture, commit=commit)
    return {
        "id": id,
        "category": category,
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "difficulty_score": difficulty_score,
        "language": language,
        "repository": repository,
        "input": {
            "prompt": prompt,
            "repository_url": repository["url"],
            "repository_ref": repository["commit_sha"],
            "files": files,
            "context": {"repo_path": repository["local_path"], "fixture": fixture},
        },
        "expected_output": expected_output
        or {"content": gold.get("content", ""), "artifacts": {}},
        "gold_answer": gold,
        "alternate_gold_answers": alternate_gold_answers or [],
        "expected_tool_calls": expected_tool_calls,
        "failure_examples": failure_examples,
        "tags": tags
        or ["v1", "curated", category.replace("_", "-"), language, fixture],
        "estimated_duration": estimated_duration,
        "task_version": "1.0.0",
        "dataset_version": "v1",
        "prompt_version": "1.0.0",
        "prompt_ids": list(DEFAULT_PROMPTS),
        "metadata": {
            "title": title,
            "description": description,
            "language": language,
            "tags": tags or [],
            "source": "githubbench-delta-v1",
            "extra": {"workflow": category, "fixture": fixture},
        },
    }
