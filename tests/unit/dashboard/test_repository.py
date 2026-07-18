"""ExperimentRepository tests."""

from __future__ import annotations

from githubbench_delta.dashboard.repository import ExperimentRepository


def test_list_and_get_experiment(repo: ExperimentRepository) -> None:
    items, total = repo.list_experiments()
    assert total == 1
    assert items[0].experiment_id == "exp_test001"
    detail = repo.get_experiment("exp_test001")
    assert detail is not None
    assert detail.summary["evaluation_count"] == 2
    assert "experiment.json" in detail.artifacts


def test_evaluations_and_trajectories(repo: ExperimentRepository) -> None:
    rows, total = repo.list_evaluations("exp_test001", sort="overall_score", order="desc")
    assert total == 2
    assert rows[0].agent_id == "codex"
    assert rows[0].latency_ms == 120.0
    trajs = repo.list_trajectories("exp_test001")
    assert len(trajs) == 2
    detail = repo.get_trajectory("exp_test001", "gb-repository-search-001::codex::0")
    assert detail is not None
    assert detail.tool_calls
    assert "plan" in detail.plan.lower() or detail.plan


def test_task_metadata_enrichment(repo: ExperimentRepository) -> None:
    detail = repo.get_experiment("exp_test001")
    assert detail is not None
    meta = repo.load_task_metadata(detail.experiment["dataset_path"])
    assert "gb-repository-search-001" in meta
    assert meta["gb-repository-search-001"]["category"] == "repository_search"


def test_settings_snapshot(repo: ExperimentRepository) -> None:
    snap = repo.settings_snapshot()
    assert snap.auth_enabled is False
    assert snap.websocket_enabled is False
    assert "experiments" in snap.results_dir
