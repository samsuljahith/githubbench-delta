"""ResultStore JSONL + SQLite + composite tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.models import (
    AgentId,
    AgentResult,
    EvaluationResult,
    MetricGroup,
    MetricResult,
    TaskOutput,
    TrialKey,
)
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit
from githubbench_delta.storage.results import create_result_store


def _eval() -> EvaluationResult:
    return EvaluationResult(
        trial=TrialKey(task_id="t1", agent_id=AgentId.CODEX),
        metric_results={
            "task_resolution": MetricResult(
                metric_id="task_resolution",
                display_name="Task Resolution",
                group=MetricGroup.CORRECTNESS,
                score=0.8,
            )
        },
        overall_score=0.8,
        group_scores={"correctness": 0.8},
    )


def test_composite_round_trip(tmp_path: Path) -> None:
    store = create_result_store(
        experiment_dir=tmp_path / "exp1",
        sqlite_path=tmp_path / "results.db",
    )
    unit = WorkUnit(task_id="t1", agent_id="codex", trial_index=0)
    ar = AgentResult(
        agent_id=AgentId.CODEX,
        task_id="t1",
        success=True,
        output=TaskOutput(content="hello"),
    )
    ev = _eval()
    store.save_trajectory(experiment_id="exp1", run_id="run1", unit=unit, agent_result=ar)
    store.save_evaluation(
        experiment_id="exp1",
        run_id="run1",
        unit=unit,
        evaluation=ev,
        agent_result=ar,
    )
    store.mark_unit_complete(experiment_id="exp1", run_id="run1", unit=unit, success=True)
    assert store.is_unit_complete(experiment_id="exp1", run_id="run1", unit=unit)
    rows = store.list_evaluations(experiment_id="exp1", run_id="run1")
    assert len(rows) == 1
    assert rows[0]["evaluation"]["overall_score"] == 0.8
    assert (tmp_path / "exp1" / "evaluation_results.json").is_file()
    assert (tmp_path / "exp1" / "trajectory.jsonl").is_file()
    loaded = store.load_agent_result(unit)
    assert loaded is not None
    assert loaded.output.content == "hello"
    store.put_cache_entry(
        CachedEvaluation(
            cache_key="k1",
            agent_result=ar.model_dump(mode="json"),
            evaluation_result=ev.model_dump(mode="json"),
        )
    )
    assert store.get_cache_entry("k1") is not None
    store.close()
