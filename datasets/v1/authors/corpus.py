"""Assemble the curated 60-task GitHubBench-Delta v1 corpus.

Tasks are authored by language for easier maintenance and v2 builds:
``python_tasks``, ``typescript_tasks``, ``go_tasks``, ``rust_tasks``,
``java_tasks``, plus optional ``edge_cases``.
"""

from __future__ import annotations

from typing import Any

from edge_cases import tasks as edge_case_tasks  # type: ignore
from go_tasks import tasks as go_tasks  # type: ignore
from java_tasks import tasks as java_tasks  # type: ignore
from python_tasks import tasks as python_tasks  # type: ignore
from rust_tasks import tasks as rust_tasks  # type: ignore
from typescript_tasks import tasks as typescript_tasks  # type: ignore


def all_tasks() -> list[dict[str, Any]]:
    """Return exactly 60 curated task records (stable category order)."""

    tasks = [
        *python_tasks(),
        *typescript_tasks(),
        *go_tasks(),
        *rust_tasks(),
        *java_tasks(),
        *edge_case_tasks(),
    ]

    def sort_key(rec: dict[str, Any]) -> tuple[str, int]:
        tid = rec["id"]  # gb-{category}-{nnn}
        parts = tid.split("-")
        num = int(parts[-1])
        cat = "-".join(parts[1:-1])
        return cat, num

    tasks = sorted(tasks, key=sort_key)
    if len(tasks) != 60:
        raise RuntimeError(f"Expected 60 tasks, got {len(tasks)}")
    return tasks


__all__ = ["all_tasks"]
