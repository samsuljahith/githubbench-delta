"""Importable helpers for metric unit tests."""

from __future__ import annotations

from githubbench_delta.core.config import EvaluatorConfig, load_config
from githubbench_delta.core.models import (
    AgentId,
    AgentMetrics,
    AgentResult,
    DiffStats,
    ExpectedToolCall,
    GoldAnswer,
    SandboxEvent,
    TaskOutput,
    ToolCall,
    ToolResult,
    Trajectory,
    TrajectoryStep,
    TrialKey,
)
from githubbench_delta.metrics.base import MetricContext, TaskSnapshot
from githubbench_delta.metrics.registry import create_metric


def get_app_config():
    return load_config()


def make_config(metric_id: str, app_config=None, **overrides) -> EvaluatorConfig:
    app_config = app_config or get_app_config()
    base = app_config.evaluators[metric_id]
    data = base.model_dump()
    data.update(overrides)
    return EvaluatorConfig.model_validate(data)


def make_metric(metric_id: str, app_config=None, **overrides):
    return create_metric(make_config(metric_id, app_config, **overrides))


def make_context(
    *,
    response: str = "widgetcli/store.py defines WidgetStore.add",
    success: bool = True,
    gold: GoldAnswer | None = None,
    expected_tools: list[ExpectedToolCall] | None = None,
    tool_names: list[str] | None = None,
    tool_failures: list[bool] | None = None,
    diff: DiffStats | None = None,
    sandbox_events: list[SandboxEvent] | None = None,
    peer_results: list[AgentResult] | None = None,
    confidence: float | None = None,
    cost_usd: float = 0.0,
    agent_id: AgentId = AgentId.CODEX,
    task_files: list[str] | None = None,
    failure_examples=None,
    alternate_golds=None,
    retries: int = 0,
    run_metadata: dict | None = None,
    peer_evaluations=None,
) -> MetricContext:
    names = tool_names or []
    fails = tool_failures or [False] * len(names)
    steps: list[TrajectoryStep] = []
    for i, name in enumerate(names):
        call = ToolCall(id=f"c{i}", name=name, arguments={"path": "x"})
        ok = not (fails[i] if i < len(fails) else False)
        result = ToolResult(
            call_id=call.id,
            name=name,
            success=ok,
            output="widgetcli/store.py\nWidgetStore.add\ndef add" if ok else "error",
            error=None if ok else "boom",
        )
        steps.append(
            TrajectoryStep(
                index=i,
                kind="tool",
                tool_call=call,
                tool_result=result,
            )
        )

    traj = Trajectory(agent_id=agent_id, task_id="t1", steps=steps)
    result = AgentResult(
        agent_id=agent_id,
        task_id="t1",
        success=success,
        output=TaskOutput(content=response, confidence=confidence),
        trajectory=traj,
        diff_stats=diff,
        sandbox_events=sandbox_events or [],
        metrics=AgentMetrics(
            latency_ms=100.0,
            total_tokens=200,
            estimated_cost_usd=cost_usd,
            tool_call_count=len(names),
        ),
        metadata={"retries": retries},
    )
    gold = gold or GoldAnswer(
        content="widgetcli/store.py defines WidgetStore.add(name).",
        acceptance_criteria=["widgetcli/store.py", "add"],
    )
    return MetricContext.from_agent_result(
        agent_result=result,
        trial=TrialKey(task_id="t1", agent_id=agent_id, trial_index=0, seed=1),
        gold_answer=gold,
        alternate_gold_answers=alternate_golds or [],
        expected_tool_calls=expected_tools or [],
        failure_examples=failure_examples or [],
        task=TaskSnapshot(
            id="t1",
            category="bug_fix",
            prompt="Find WidgetStore.add",
            files=task_files or ["widgetcli/store.py"],
            language="python",
        ),
        peer_results=peer_results or [],
        peer_evaluations=peer_evaluations or [],
        run_metadata=run_metadata or {},
    )
