"""Pipeline stages and cache helper tests."""

from __future__ import annotations

import pytest

from githubbench_delta.core.config import load_config
from githubbench_delta.core.models import AgentId, AgentResult, TaskOutput
from githubbench_delta.pipeline.base import (
    AggregatorStage,
    MetricEngineStage,
    PipelineContext,
    PipelineOrchestrator,
    default_pipeline_stages,
)
from githubbench_delta.pipeline.cache import make_cache_key, unit_seed
from githubbench_delta.pipeline.models import ExperimentSpec


def test_unit_seed_deterministic() -> None:
    a = unit_seed(42, "t1", "codex", 0)
    b = unit_seed(42, "t1", "codex", 0)
    c = unit_seed(42, "t1", "codex", 1)
    assert a == b
    assert a != c


def test_cache_key_changes_with_content() -> None:
    r1 = AgentResult(
        agent_id=AgentId.CODEX,
        task_id="t1",
        output=TaskOutput(content="a"),
    )
    r2 = AgentResult(
        agent_id=AgentId.CODEX,
        task_id="t1",
        output=TaskOutput(content="b"),
    )
    k1 = make_cache_key(task_id="t1", agent_id="codex", trial_index=0, seed=1, agent_result=r1)
    k2 = make_cache_key(task_id="t1", agent_id="codex", trial_index=0, seed=1, agent_result=r2)
    assert k1 != k2


@pytest.mark.asyncio
async def test_metric_and_aggregator_stages_delegate() -> None:
    ctx = PipelineContext(run_id="r1")
    ctx = await MetricEngineStage().run(ctx)
    ctx = await AggregatorStage().run(ctx)
    assert ctx.artifacts["metric_engine"]
    assert ctx.artifacts["aggregator"]


def test_default_stages_exclude_dashboard() -> None:
    names = [s.name.value for s in default_pipeline_stages()]
    assert "dashboard" not in names
    assert "html_report" not in names
    assert "agent" in names


def test_pipeline_config_loaded() -> None:
    cfg = load_config()
    assert cfg.runtime.pipeline.max_concurrency >= 1
    assert cfg.runtime.pipeline.results_dir


@pytest.mark.asyncio
async def test_orchestrator_requires_stages() -> None:
    with pytest.raises(Exception, match="no stages"):
        await PipelineOrchestrator([]).run(PipelineContext(run_id="x"))


def test_experiment_spec_defaults() -> None:
    spec = ExperimentSpec(dataset_path="datasets/v1")
    assert spec.trial_count == 1
    assert spec.resume is True
