"""Storage helpers and event/result persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from githubbench_delta.storage.events import (
    DuckDBEventStore,
    EventStore,
    JSONLEventStore,
    SQLiteEventStore,
    create_event_store,
)
from githubbench_delta.storage.paths import (
    ensure_runtime_dirs,
    resolve_duckdb_path,
    resolve_sqlite_path,
)

if TYPE_CHECKING:
    from githubbench_delta.storage.results import (
        CompositeResultStore,
        JSONLResultStore,
        ResultStore,
        SQLiteResultStore,
        create_result_store,
    )

__all__ = [
    "ensure_runtime_dirs",
    "resolve_duckdb_path",
    "resolve_sqlite_path",
    "EventStore",
    "JSONLEventStore",
    "SQLiteEventStore",
    "DuckDBEventStore",
    "create_event_store",
    "CompositeResultStore",
    "JSONLResultStore",
    "ResultStore",
    "SQLiteResultStore",
    "create_result_store",
]


def __getattr__(name: str) -> Any:
    if name in {
        "CompositeResultStore",
        "JSONLResultStore",
        "ResultStore",
        "SQLiteResultStore",
        "create_result_store",
    }:
        from githubbench_delta.storage import results as results_mod

        return getattr(results_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
