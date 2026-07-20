"""Ingest + decay edge-case tests for observatory."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from githubbench_delta.observatory.decay import DecayModel
from githubbench_delta.observatory.ingest import snapshots_from_experiment
from githubbench_delta.observatory.models import BenchmarkSnapshot, MetricSummary


def test_decay_non_positive_lambda() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    timestamps = [t0 + timedelta(days=d) for d in (0, 10, 20)]
    # Growing differentiation → non-decaying (λ ≤ 0)
    diffs = [0.1, 0.2, 0.3]
    curve = DecayModel().fit(timestamps, diffs)
    assert curve.lambda_per_day <= 0
    assert DecayModel().half_life_days(curve) is None


def test_decay_single_point() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    curve = DecayModel().fit([t0], [0.2])
    assert curve.points == []
    assert DecayModel().half_life_days(curve) is None


def test_snapshots_from_missing_experiment(tmp_path: Path) -> None:
    snaps = snapshots_from_experiment("exp_does_not_exist", results_dir=tmp_path)
    assert snaps == []


def test_snapshots_from_minimal_experiment(tmp_path: Path) -> None:
    eid = "exp_obs_fixture"
    exp_dir = tmp_path / eid
    exp_dir.mkdir()
    (exp_dir / "experiment.json").write_text(
        json.dumps(
            {
                "experiment_id": eid,
                "created_at": "2026-01-15T12:00:00Z",
                "updated_at": "2026-01-15T12:30:00Z",
                "dataset_path": "datasets/v1",
                "status": "completed",
            }
        ),
        encoding="utf-8",
    )
    (exp_dir / "evaluation_results.json").write_text(
        json.dumps(
            [
                {
                    "experiment_id": eid,
                    "run_id": "run1",
                    "unit_key": "t1::minicpm::0",
                    "task_id": "t1",
                    "agent_id": "minicpm",
                    "trial_index": 0,
                    "evaluation": {
                        "overall_score": 0.55,
                        "confidence_score": 0.8,
                        "group_scores": {"correctness": 0.6},
                        "metric_results": {
                            "task_resolution": {"score": 0.5, "skipped": False},
                        },
                        "metadata": {},
                    },
                    "agent_result_summary": {"success": True},
                },
                {
                    "experiment_id": eid,
                    "run_id": "run1",
                    "unit_key": "t1::codex::0",
                    "task_id": "t1",
                    "agent_id": "codex",
                    "trial_index": 0,
                    "evaluation": {
                        "overall_score": 0.72,
                        "confidence_score": 0.9,
                        "group_scores": {"correctness": 0.7},
                        "metric_results": {
                            "task_resolution": {"score": 0.8, "skipped": False},
                        },
                        "metadata": {},
                    },
                    "agent_result_summary": {"success": True},
                },
            ]
        ),
        encoding="utf-8",
    )
    snaps = snapshots_from_experiment(eid, results_dir=tmp_path)
    assert len(snaps) == 2
    by_agent = {s.agent_id: s for s in snaps}
    assert by_agent["minicpm"].score == pytest.approx(0.55)
    assert by_agent["codex"].score == pytest.approx(0.72)
    assert by_agent["minicpm"].experiment_id == eid
    assert "0.1.0" in by_agent["minicpm"].benchmark_version


def test_snapshot_history_key() -> None:
    s = BenchmarkSnapshot(
        snapshot_id="s1",
        timestamp=datetime.now(UTC),
        benchmark_version="0.1.0",
        experiment_id="exp_a",
        agent_id="minicpm",
        model="m",
        provider="p",
        score=0.5,
        metric_summary=MetricSummary(),
    )
    assert s.history_key == "exp_a::minicpm"
