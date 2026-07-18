"""Evaluation result persistence."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.storage.results.base import ResultStore
from githubbench_delta.storage.results.composite import CompositeResultStore
from githubbench_delta.storage.results.jsonl_store import JSONLResultStore
from githubbench_delta.storage.results.sqlite_store import SQLiteResultStore


def create_result_store(
    *,
    experiment_dir: Path | str,
    sqlite_path: Path | str,
) -> CompositeResultStore:
    """Create the default dual-write ResultStore for an experiment."""

    return CompositeResultStore(
        JSONLResultStore(experiment_dir),
        SQLiteResultStore(sqlite_path),
    )


__all__ = [
    "CompositeResultStore",
    "JSONLResultStore",
    "ResultStore",
    "SQLiteResultStore",
    "create_result_store",
]
