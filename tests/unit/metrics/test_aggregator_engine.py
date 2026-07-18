"""Aggregator and EvaluationEngine tests."""

from __future__ import annotations

from githubbench_delta.core.models import AgentId, MetricGroup, MetricResult, TrialKey
from githubbench_delta.metrics.aggregator import MetricAggregator, WeightedScore
from githubbench_delta.metrics.engine import EvaluationEngine
from githubbench_delta.metrics.registry import MetricRegistry

from .helpers import make_context, make_metric


def test_aggregator_weighted_average() -> None:
    results = [
        MetricResult(
            metric_id="a",
            display_name="A",
            group=MetricGroup.CORRECTNESS,
            score=1.0,
            weight=1.0,
        ),
        MetricResult(
            metric_id="b",
            display_name="B",
            group=MetricGroup.TRAJECTORY,
            score=0.0,
            weight=1.0,
        ),
        MetricResult(
            metric_id="c",
            display_name="C",
            group=MetricGroup.CORRECTNESS,
            score=0.5,
            weight=2.0,
            skipped=True,
            skip_reason="x",
        ),
    ]
    out = MetricAggregator().aggregate(results)
    assert out.overall_score == 0.5
    assert "correctness" in out.group_scores
    assert out.group_scores["correctness"] == 1.0
    assert any(isinstance(w, WeightedScore) for w in out.weighted_scores)


def test_evaluation_engine_runs_all(app_config) -> None:
    engine = EvaluationEngine(MetricRegistry.from_app_config(app_config))
    ctx = make_context(
        response="widgetcli/store.py add WidgetStore",
        tool_names=["search_repository", "read_file"],
        success=True,
    )
    result = engine.evaluate(ctx)
    assert result.overall_score is not None
    assert 0.0 <= result.overall_score <= 1.0
    assert result.group_scores
    assert result.confidence_score is not None
    # peer metrics may be skipped but still present
    assert "task_resolution" in result.metric_results
    assert len(result.metric_results) == 18


def test_metric_metadata_and_reasoning(app_config) -> None:
    m = make_metric("task_resolution", app_config)
    meta = m.metadata()
    assert meta["id"] == "task_resolution"
    assert meta["version"] == "1.0.0"
    ctx = make_context()
    assert isinstance(m.reasoning(ctx), str)
    assert isinstance(m.details(ctx), dict)
    assert 0.0 <= m.score(ctx) <= 1.0


def test_registry_enabled_filter(app_config) -> None:
    cfg = app_config.model_copy(deep=True)
    cfg.evaluators["task_resolution"].enabled = False
    registry = MetricRegistry.from_app_config(cfg)
    enabled_ids = {m.id for m in registry.enabled_metrics()}
    assert "task_resolution" not in enabled_ids
    assert len(enabled_ids) == 17


def test_context_factory_populates_fields() -> None:
    ctx = make_context(tool_names=["read_file"], cost_usd=0.01)
    assert ctx.tool_calls
    assert ctx.response
    assert ctx.token_usage.total_tokens > 0
    assert ctx.cost_usd == 0.01
    assert ctx.task is not None
    assert ctx.trial.task_id == "t1"


def test_aggregator_to_evaluation_result() -> None:
    trial = TrialKey(task_id="t1", agent_id=AgentId.MINICPM)
    results = [
        MetricResult(
            metric_id="task_resolution",
            display_name="Task Resolution",
            group=MetricGroup.CORRECTNESS,
            score=0.8,
            weight=1.0,
            confidence=0.9,
        )
    ]
    ev = MetricAggregator().to_evaluation_result(trial, results, category="bug_fix")
    assert ev.overall_score == 0.8
    assert ev.metadata["category"] == "bug_fix"
