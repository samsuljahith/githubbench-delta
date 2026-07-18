"""Pydantic domain model round-trip tests."""

from __future__ import annotations

from githubbench_delta.core.models import (
    AgentId,
    AgentMetrics,
    AgentResult,
    Difficulty,
    DiffStats,
    GoldAnswer,
    MetricGroup,
    MetricResult,
    SandboxEvent,
    TaskCategory,
    TaskInput,
    TaskMetadata,
    TaskOutput,
    ToolCall,
    ToolResult,
    Trajectory,
    TrajectoryStep,
    TrialKey,
)
from githubbench_delta.metrics.base import MetricContext
from githubbench_delta.tasks.registry import create_task


def test_agent_result_round_trip() -> None:
    result = AgentResult(
        agent_id=AgentId.CLAUDE,
        task_id="t1",
        success=True,
        output=TaskOutput(content="fixed", confidence=0.8),
        trajectory=Trajectory(
            agent_id=AgentId.CLAUDE,
            task_id="t1",
            steps=[
                TrajectoryStep(
                    index=0,
                    kind="tool",
                    tool_call=ToolCall(
                        id="c1",
                        name="read_file",
                        arguments={"path": "a.py"},
                    ),
                    tool_result=ToolResult(
                        call_id="c1",
                        name="read_file",
                        success=True,
                        output="x",
                    ),
                )
            ],
        ),
        diff_stats=DiffStats(changed_files=["a.py"], insertions=3, deletions=1),
        sandbox_events=[SandboxEvent(kind="branch_write", message="attempted main", allowed=False)],
        metrics=AgentMetrics(latency_ms=12.5, total_tokens=100, tool_call_count=1),
    )
    restored = AgentResult.model_validate_json(result.model_dump_json())
    assert restored.agent_id == AgentId.CLAUDE
    assert restored.diff_stats is not None
    assert restored.diff_stats.changed_files == ["a.py"]
    assert restored.trajectory is not None
    assert len(restored.trajectory.steps) == 1


def test_metric_result_and_trial_key() -> None:
    trial = TrialKey(task_id="t1", agent_id=AgentId.MINICPM, trial_index=1, seed=7)
    metric = MetricResult(
        metric_id="task_resolution",
        display_name="Task Resolution",
        group=MetricGroup.CORRECTNESS,
        score=0.0,
        details={"status": "not_implemented"},
    )
    assert trial.model_dump()["agent_id"] == "minicpm"
    assert metric.group == MetricGroup.CORRECTNESS


def test_metric_context_fields() -> None:
    ctx = MetricContext(
        trial=TrialKey(task_id="t1", agent_id=AgentId.CODEX),
        task_id="t1",
        gold_answer=GoldAnswer(content="ok", acceptance_criteria=["passes tests"]),
        agent_result=AgentResult(agent_id=AgentId.CODEX, task_id="t1"),
        diff_stats=DiffStats(changed_files=["x.py"]),
        peer_results=[],
    )
    assert ctx.diff_stats is not None
    assert ctx.gold_answer is not None
    assert "diff_stats" in MetricContext.model_fields
    assert "peer_results" in MetricContext.model_fields
    assert "sandbox_events" in MetricContext.model_fields


def test_create_bug_fix_task() -> None:
    task = create_task(
        TaskCategory.BUG_FIX,
        id="bug-1",
        input=TaskInput(prompt="Fix the off-by-one error"),
        difficulty=Difficulty.HARD,
        metadata=TaskMetadata(title="Off by one"),
    )
    assert task.category == TaskCategory.BUG_FIX
    assert "off-by-one" in task.to_prompt().lower()
