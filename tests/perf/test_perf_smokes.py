"""Lightweight performance smoke tests (generous budgets)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.unit.metrics.helpers import make_context

from githubbench_delta.api.app import create_app
from githubbench_delta.core.config import load_config
from githubbench_delta.core.models import AgentId
from githubbench_delta.datasets.validators import DatasetValidator
from githubbench_delta.metrics.engine import EvaluationEngine
from githubbench_delta.metrics.registry import MetricRegistry
from githubbench_delta.pipeline.experiment import ExperimentRunner
from githubbench_delta.pipeline.models import ExperimentSpec
from githubbench_delta.reports.builder import ReportBuilder
from githubbench_delta.reports.models import ReportRequest, ReportType

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.perf
def test_perf_dataset_validate() -> None:
    from githubbench_delta.benchmark.runner import BenchmarkRunner

    path = ROOT / "datasets" / "v1"
    start = time.perf_counter()
    runner = BenchmarkRunner(base_path=ROOT, validate=False)
    catalog = runner.load_dataset(path)
    DatasetValidator(base_path=ROOT, strict_corpus=False).validate_tasks(
        catalog.all(), metadata=runner.metadata
    )
    elapsed = time.perf_counter() - start
    assert len(catalog) > 0
    assert elapsed < 5.0, f"dataset validate took {elapsed:.2f}s"


@pytest.mark.perf
def test_perf_evaluation_engine(app_config) -> None:
    engine = EvaluationEngine(MetricRegistry.from_app_config(app_config))
    ctx = make_context(
        response="widgetcli/store.py add WidgetStore",
        tool_names=["search_repository", "read_file"],
        success=True,
    )
    start = time.perf_counter()
    result = engine.evaluate(ctx)
    elapsed = time.perf_counter() - start
    assert result.overall_score is not None
    assert elapsed < 2.0, f"evaluation took {elapsed:.2f}s"


@pytest.mark.perf
@pytest.mark.asyncio
async def test_perf_pipeline_dry_run(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    runner = ExperimentRunner(app_config=cfg)
    start = time.perf_counter()
    await runner.run(
        ExperimentSpec(
            dataset_path=ROOT / "datasets" / "v1",
            agent_ids=[AgentId.CODEX.value],
            task_ids=["gb-repository-search-001"],
            trial_count=1,
            seed=42,
            dry_run=True,
            resume=False,
            use_cache=False,
        )
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 15.0, f"dry-run took {elapsed:.2f}s"


@pytest.mark.perf
def test_perf_report_generation(tmp_path: Path) -> None:
    from tests.unit.reports.conftest import _write_experiment

    root = tmp_path / "experiments"
    _write_experiment(root, "exp_perf", codex_score=0.9, minicpm_score=0.7)
    request = ReportRequest(
        experiment_ids=["exp_perf"],
        report_type=ReportType.EXECUTIVE,
        formats=["markdown", "json"],
        output_dir=tmp_path / "out",
        results_dir=root,
        sqlite_path=tmp_path / "unused.db",
    )
    start = time.perf_counter()
    paths = ReportBuilder().generate(request)
    elapsed = time.perf_counter() - start
    assert paths
    assert elapsed < 5.0, f"report generation took {elapsed:.2f}s"


@pytest.mark.perf
def test_perf_dashboard_startup() -> None:
    start = time.perf_counter()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/dashboard/health")
    elapsed = time.perf_counter() - start
    assert resp.status_code == 200
    assert elapsed < 3.0, f"dashboard startup took {elapsed:.2f}s"
