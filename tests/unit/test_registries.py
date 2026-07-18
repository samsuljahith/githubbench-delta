"""Registry catalog tests for agents, tasks, and methodology metrics."""

from __future__ import annotations

from githubbench_delta.agents.registry import list_agent_ids
from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS
from githubbench_delta.core.models import AgentId, MetricGroup, TaskCategory
from githubbench_delta.metrics.registry import (
    catalog_entries,
    create_metrics_from_app_config,
    get_metric_group,
    list_metric_ids,
)
from githubbench_delta.tasks.registry import list_task_categories

GENERIC_METRIC_IDS = {
    "exact_match",
    "semantic_similarity",
    "functional_correctness",
    "tool_use_accuracy",
    "plan_adherence",
    "trajectory_coherence",
}


def test_agent_registry() -> None:
    assert list_agent_ids() == [AgentId.MINICPM, AgentId.CLAUDE, AgentId.CODEX]


def test_task_registry() -> None:
    categories = list_task_categories()
    assert len(categories) == len(TaskCategory)
    assert set(categories) == set(TaskCategory)
    assert TaskCategory.CODE_EXPLANATION in categories
    assert TaskCategory.ISSUE_ANALYSIS in categories
    assert TaskCategory.PULL_REQUEST_REVIEW in categories


def test_metric_registry_exactly_methodology_ids() -> None:
    ids = list_metric_ids()
    assert ids == list(METHODOLOGY_METRIC_IDS)
    assert len(ids) == 18
    assert GENERIC_METRIC_IDS.isdisjoint(ids)


def test_metric_groups(app_config) -> None:
    expected = {
        "task_resolution": MetricGroup.CORRECTNESS,
        "engineering_usefulness": MetricGroup.CORRECTNESS,
        "diff_minimality": MetricGroup.CORRECTNESS,
        "tool_economy": MetricGroup.TRAJECTORY,
        "unnecessary_tool_calls": MetricGroup.TRAJECTORY,
        "planning_quality": MetricGroup.TRAJECTORY,
        "branch_safety": MetricGroup.SAFETY,
        "blast_radius": MetricGroup.SAFETY,
        "safe_failure": MetricGroup.SAFETY,
        "grounding_ratio": MetricGroup.GROUNDING,
        "hallucinated_api": MetricGroup.GROUNDING,
        "test_honesty": MetricGroup.GROUNDING,
        "recovery_score": MetricGroup.RELIABILITY,
        "calibration": MetricGroup.RELIABILITY,
        "cross_trial_consistency": MetricGroup.RELIABILITY,
        "reproducibility": MetricGroup.EFFICIENCY,
        "cost_normalized_capability": MetricGroup.EFFICIENCY,
        "local_vs_hosted_parity": MetricGroup.EFFICIENCY,
    }
    for metric_id, group in expected.items():
        assert get_metric_group(metric_id) == group
        assert app_config.evaluators[metric_id].group == group


def test_create_all_metric_instances(app_config) -> None:
    metrics = create_metrics_from_app_config(app_config)
    assert set(metrics) == set(METHODOLOGY_METRIC_IDS)
    for metric_id, metric in metrics.items():
        assert metric.id == metric_id


def test_catalog_entries(app_config) -> None:
    rows = catalog_entries(app_config)
    assert len(rows) == 18
    assert {row["id"] for row in rows} == set(METHODOLOGY_METRIC_IDS)
