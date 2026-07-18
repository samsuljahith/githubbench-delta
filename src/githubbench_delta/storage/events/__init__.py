"""Event persistence backends."""

from pathlib import Path

from githubbench_delta.core.config import EventStoreConfig
from githubbench_delta.core.errors import ConfigurationError
from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.storage.events.duckdb_store import DuckDBEventStore
from githubbench_delta.storage.events.jsonl_store import JSONLEventStore
from githubbench_delta.storage.events.sqlite_store import SQLiteEventStore


def create_event_store(config: EventStoreConfig) -> EventStore:
    """Factory for configured event store backends."""

    backend = config.backend.lower().strip()
    if backend == "jsonl":
        return JSONLEventStore(config.jsonl_path)
    if backend == "sqlite":
        return SQLiteEventStore(config.sqlite_path)
    if backend == "duckdb":
        return DuckDBEventStore(Path(config.sqlite_path).with_suffix(".duckdb"))
    raise ConfigurationError(f"Unknown event_store.backend: {config.backend!r}")


__all__ = [
    "EventStore",
    "JSONLEventStore",
    "SQLiteEventStore",
    "DuckDBEventStore",
    "create_event_store",
]
