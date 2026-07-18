"""Trajectory logger tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.models import AgentId
from githubbench_delta.observability.context import bind_context
from githubbench_delta.storage.events.jsonl_store import JSONLEventStore
from githubbench_delta.trajectory.events import LifecycleStage
from githubbench_delta.trajectory.logger import TrajectoryLogger


def test_logger_emits_parent_child_and_projects_trajectory(tmp_path: Path) -> None:
    store = JSONLEventStore(tmp_path / "e.jsonl")
    with bind_context(run_id="run_x", agent_id="minicpm", task_id="task-1") as ctx:
        logger = TrajectoryLogger(
            run_id=ctx.run_id,
            agent_id=AgentId.MINICPM,
            task_id="task-1",
            event_store=store,
        )
        logger.emit(LifecycleStage.INITIALIZE, result="ok")
        parent = logger.emit(LifecycleStage.PROVIDER, result="thinking", content="thinking")
        logger.emit(
            LifecycleStage.TOOL,
            tool="read_file",
            arguments={"path": "README.md"},
            result="hello",
            latency_ms=5.0,
            parent_trace_id=parent.trace_id,
        )
        traj = logger.build_trajectory()

    assert len(logger.events) == 3
    assert logger.events[2].parent_trace_id == parent.trace_id
    assert logger.events[2].tool == "read_file"
    assert traj.task_id == "task-1"
    assert any(step.kind == "tool" for step in traj.steps)
    persisted = store.query(run_id="run_x")
    assert len(persisted) == 3
    assert all(e.event_id for e in persisted)
