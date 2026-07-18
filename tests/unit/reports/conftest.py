"""Fixtures for report tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from githubbench_delta.dashboard.repository import ExperimentRepository


def _write_experiment(root: Path, exp_id: str, *, codex_score: float, minicpm_score: float) -> Path:
    exp = root / exp_id
    exp.mkdir(parents=True)
    (exp / "experiment.json").write_text(
        json.dumps(
            {
                "experiment_id": exp_id,
                "name": "fixture",
                "status": "completed",
                "seed": 1,
                "trial_count": 1,
                "agent_ids": ["codex", "minicpm"],
                "task_ids": ["gb-repository-search-001"],
                "dataset_path": str(Path(__file__).resolve().parents[3] / "datasets" / "v1"),
                "metadata": {
                    "dataset_version": "v1",
                    "prompt_version": "p1",
                },
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:01Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (exp / "run.json").write_text(
        json.dumps(
            {
                "run_id": f"run_{exp_id}",
                "experiment_id": exp_id,
                "status": "completed",
                "units_total": 2,
                "units_done": 2,
                "units_failed": 0,
                "completed_units": [
                    "gb-repository-search-001::codex::0",
                    "gb-repository-search-001::minicpm::0",
                ],
                "seed": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def eval_row(agent: str, score: float) -> dict:
        return {
            "experiment_id": exp_id,
            "run_id": f"run_{exp_id}",
            "unit_key": f"gb-repository-search-001::{agent}::0",
            "task_id": "gb-repository-search-001",
            "agent_id": agent,
            "trial_index": 0,
            "agent_result_summary": {"success": True, "error": None},
            "evaluation": {
                "overall_score": score,
                "confidence_score": 0.8,
                "group_scores": {
                    "correctness": score,
                    "trajectory": 0.5,
                    "safety": 1.0,
                    "grounding": 0.9,
                    "reliability": 0.7,
                    "efficiency": 0.6,
                },
                "metadata": {"category": "repository_search"},
                "metric_results": {
                    "task_resolution": {
                        "metric_id": "task_resolution",
                        "score": score,
                        "skipped": False,
                        "weight": 1.0,
                    },
                    "engineering_usefulness": {
                        "metric_id": "engineering_usefulness",
                        "score": score * 0.9,
                        "skipped": False,
                        "weight": 1.0,
                    },
                    "diff_minimality": {
                        "metric_id": "diff_minimality",
                        "score": 1.0,
                        "skipped": False,
                        "weight": 1.0,
                    },
                    "calibration": {
                        "metric_id": "calibration",
                        "score": 0.4,
                        "skipped": False,
                        "weight": 1.0,
                    },
                },
            },
        }

    (exp / "evaluation_results.json").write_text(
        json.dumps(
            [eval_row("codex", codex_score), eval_row("minicpm", minicpm_score)],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    traj_lines = []
    for agent, lat, cost in (
        ("codex", 120.0, 0.01),
        ("minicpm", 80.0, 0.0),
    ):
        traj_lines.append(
            json.dumps(
                {
                    "experiment_id": exp_id,
                    "run_id": f"run_{exp_id}",
                    "unit_key": f"gb-repository-search-001::{agent}::0",
                    "task_id": "gb-repository-search-001",
                    "agent_id": agent,
                    "trial_index": 0,
                    "agent_result": {
                        "agent_id": agent,
                        "task_id": "gb-repository-search-001",
                        "trial_index": 0,
                        "success": True,
                        "output": {"content": f"answer from {agent}"},
                        "metrics": {
                            "latency_ms": lat,
                            "estimated_cost_usd": cost,
                        },
                        "metadata": {"retries": 0},
                        "trajectory": {
                            "steps": [
                                {
                                    "index": 0,
                                    "kind": "tool",
                                    "tool_call": {
                                        "id": "c0",
                                        "name": "read_file",
                                        "arguments": {},
                                    },
                                },
                                {
                                    "index": 1,
                                    "kind": "assistant",
                                    "content": "plan: inspect store",
                                },
                            ]
                        },
                    },
                    "trajectory": {
                        "steps": [
                            {
                                "index": 0,
                                "kind": "tool",
                                "tool_call": {
                                    "id": "c0",
                                    "name": "read_file",
                                    "arguments": {},
                                },
                            },
                            {
                                "index": 1,
                                "kind": "assistant",
                                "content": "plan: inspect store",
                            },
                        ]
                    },
                }
            )
        )
    (exp / "trajectory.jsonl").write_text("\n".join(traj_lines) + "\n", encoding="utf-8")
    return exp


@pytest.fixture
def sample_results_dir(tmp_path: Path) -> Path:
    root = tmp_path / "experiments"
    _write_experiment(root, "exp_base", codex_score=0.9, minicpm_score=0.7)
    _write_experiment(root, "exp_cand", codex_score=0.6, minicpm_score=0.5)
    return root


@pytest.fixture
def repo(sample_results_dir: Path) -> ExperimentRepository:
    return ExperimentRepository(
        results_dir=sample_results_dir,
        sqlite_path=sample_results_dir.parent / "unused.db",
    )
