"""Comparison, regression, and recommendation tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.builder import ReportBuilder
from githubbench_delta.reports.compare import compare_experiments
from githubbench_delta.reports.models import ReportDocument, ReportRequest, ReportType
from githubbench_delta.reports.recommendations import generate_recommendations


def test_compare_detects_overall_regression(
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    diff = compare_experiments(repo, "exp_base", "exp_cand")
    assert diff.overall_delta is not None
    assert diff.overall_delta.delta is not None
    assert diff.overall_delta.delta < 0
    assert diff.overall_delta.is_regression is True
    assert diff.dataset_version_baseline == "v1"
    assert diff.prompt_version_baseline == "p1"


def test_regression_report_includes_diff_section(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    request = ReportRequest(
        experiment_ids=["exp_base", "exp_cand"],
        report_type=ReportType.REGRESSION,
        formats=["markdown", "json"],
        output_dir=tmp_path / "out",
        baseline_id="exp_base",
        candidate_id="exp_cand",
        results_dir=sample_results_dir,
        sqlite_path=sample_results_dir.parent / "unused.db",
    )
    doc = ReportBuilder(repo=repo).build(request)
    assert doc.diff is not None
    ids = {s.id for s in doc.sections}
    assert "diff" in ids
    assert "regressions" in ids
    assert (
        any("regress" in r.lower() or "delta" in r.lower() for r in doc.recommendations)
        or doc.recommendations
    )


def test_recommendations_flag_low_scores() -> None:
    doc = ReportDocument(
        report_type=ReportType.TECHNICAL,
        title="t",
        evaluations=[
            {
                "overall_score": 0.3,
                "confidence_score": 0.4,
                "success": True,
                "cost_usd": 0.1,
                "latency_ms": 9000.0,
                "agent_id": "codex",
                "unit_key": "t::codex::0",
            }
        ],
        leaderboard=[
            {
                "agent_id": "codex",
                "overall_score": 0.3,
                "group_scores": {"safety": 0.2},
                "confidence": 0.4,
                "cost_usd": 0.1,
                "latency_ms": 9000.0,
                "success_rate": 1.0,
                "n_trials": 1,
            }
        ],
        metric_stats=[
            {
                "metric_id": "calibration",
                "mean": 0.2,
                "importance": 0.9,
                "n": 1,
            }
        ],
        warnings=["w1", "w2"],
    )
    recs = generate_recommendations(doc)
    assert len(recs) >= 2
    joined = " ".join(recs).lower()
    assert "overall" in joined or "group" in joined or "confidence" in joined
