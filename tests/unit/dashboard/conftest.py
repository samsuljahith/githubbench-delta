"""Fixtures for dashboard tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from githubbench_delta.dashboard.repository import ExperimentRepository


@pytest.fixture
def sample_experiment_dir(tmp_path: Path) -> Path:
    exp = tmp_path / "experiments" / "exp_test001"
    exp.mkdir(parents=True)
    (exp / "experiment.json").write_text(
        json.dumps(
            {
                "experiment_id": "exp_test001",
                "name": "fixture",
                "status": "completed",
                "seed": 1,
                "trial_count": 1,
                "agent_ids": ["codex", "minicpm"],
                "task_ids": ["gb-repository-search-001"],
                "dataset_path": str(Path(__file__).resolve().parents[3] / "datasets" / "v1"),
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
                "run_id": "run_test",
                "experiment_id": "exp_test001",
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
            "experiment_id": "exp_test001",
            "run_id": "run_test",
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
                },
            },
        }

    (exp / "evaluation_results.json").write_text(
        json.dumps([eval_row("codex", 0.9), eval_row("minicpm", 0.7)], indent=2) + "\n",
        encoding="utf-8",
    )
    traj_lines = []
    for agent in ("codex", "minicpm"):
        traj_lines.append(
            json.dumps(
                {
                    "experiment_id": "exp_test001",
                    "run_id": "run_test",
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
                            "latency_ms": 120.0 if agent == "codex" else 80.0,
                            "estimated_cost_usd": 0.01 if agent == "codex" else 0.0,
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
    return tmp_path / "experiments"


@pytest.fixture
def repo(sample_experiment_dir: Path) -> ExperimentRepository:
    return ExperimentRepository(
        results_dir=sample_experiment_dir,
        sqlite_path=sample_experiment_dir.parent / "unused.db",
    )
