"""Deterministic dry-run benchmark regression smoke (no live agents)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from githubbench_delta.core.config import load_config
from githubbench_delta.core.models import AgentId
from githubbench_delta.pipeline.experiment import ExperimentRunner
from githubbench_delta.pipeline.models import ExperimentSpec, ExperimentStatus
from githubbench_delta.reports.builder import ReportBuilder
from githubbench_delta.reports.models import ReportRequest, ReportType

# Soft floor for dry-run overall on the pinned task (gold-answer synthesis).
MIN_OVERALL_FLOOR = 0.0
PINNED_TASK = "gb-repository-search-001"
PINNED_SEED = 42


@pytest.mark.regression
@pytest.mark.asyncio
async def test_dry_run_benchmark_artifacts_and_scores(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    root = Path(__file__).resolve().parents[2]
    dataset = root / "datasets" / "v1"

    runner = ExperimentRunner(app_config=cfg)
    manifest = await runner.run(
        ExperimentSpec(
            dataset_path=dataset,
            agent_ids=[AgentId.CODEX.value],
            task_ids=[PINNED_TASK],
            trial_count=1,
            seed=PINNED_SEED,
            max_concurrency=1,
            dry_run=True,
            resume=False,
            use_cache=False,
            name="regression-dry-run",
        )
    )
    assert manifest.status == ExperimentStatus.COMPLETED
    exp_dir = cfg.runtime.pipeline.results_dir / manifest.experiment_id
    eval_path = exp_dir / "evaluation_results.json"
    assert eval_path.is_file()
    rows = json.loads(eval_path.read_text(encoding="utf-8"))
    assert len(rows) >= 1
    scores = [
        float(r["evaluation"]["overall_score"])
        for r in rows
        if r.get("evaluation", {}).get("overall_score") is not None
    ]
    assert scores
    assert min(scores) >= MIN_OVERALL_FLOOR
    assert max(scores) <= 1.0

    # CI summary report from artifacts
    request = ReportRequest(
        experiment_ids=[manifest.experiment_id],
        report_type=ReportType.CI_SUMMARY,
        formats=["markdown"],
        output_dir=tmp_path / "reports",
        results_dir=cfg.runtime.pipeline.results_dir,
        sqlite_path=tmp_path / "unused.db",
    )
    paths = ReportBuilder().generate(request)
    assert paths
    assert paths[0].is_file()
    body = paths[0].read_text(encoding="utf-8")
    assert "CI Summary" in body or "Overall" in body or "#" in body
