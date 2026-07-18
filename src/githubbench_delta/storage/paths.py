"""Path helpers for runtime artifact directories."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.config import AppConfig, PathsConfig


def ensure_runtime_dirs(paths: PathsConfig) -> None:
    """Create logs/results/reports directories if they do not exist."""

    for directory in (paths.logs, paths.results, paths.reports, paths.datasets):
        Path(directory).mkdir(parents=True, exist_ok=True)


def resolve_sqlite_path(config: AppConfig) -> Path:
    """Return the SQLite OLTP database path from config."""

    return Path(config.runtime.storage.sqlite_path)


def resolve_duckdb_path(config: AppConfig) -> Path:
    """Return the DuckDB OLAP database path from config."""

    return Path(config.runtime.storage.duckdb_path)
