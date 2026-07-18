"""Event store persistence tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.models import AgentId
from githubbench_delta.storage.events.jsonl_store import JSONLEventStore
from githubbench_delta.storage.events.sqlite_store import SQLiteEventStore
from githubbench_delta.trajectory.events import ExecutionEvent, LifecycleStage


def _event(run_id: str = "run_1", task_id: str = "t1") -> ExecutionEvent:
    return ExecutionEvent(
        run_id=run_id,
        agent_id=AgentId.MINICPM,
        task_id=task_id,
        stage=LifecycleStage.EXECUTE,
        tool="read_file",
        arguments={"path": "a.py"},
        result="ok",
        latency_ms=12.0,
    )


def test_jsonl_round_trip(tmp_path: Path) -> None:
    store = JSONLEventStore(tmp_path / "events.jsonl")
    e1 = _event()
    e2 = _event(task_id="t2")
    store.append(e1)
    store.append_many([e2])
    all_events = store.query()
    assert len(all_events) == 2
    filtered = store.query(task_id="t2")
    assert len(filtered) == 1
    assert filtered[0].task_id == "t2"
    assert filtered[0].tool == "read_file"


def test_sqlite_round_trip(tmp_path: Path) -> None:
    store = SQLiteEventStore(tmp_path / "events.db")
    e1 = _event(run_id="run_a")
    store.append(e1)
    rows = store.query(run_id="run_a")
    assert len(rows) == 1
    assert rows[0].event_id == e1.event_id
    assert rows[0].trace_id
    store.close()
