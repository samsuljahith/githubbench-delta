"""Dashboard REST API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.dashboard.api import get_repository
from githubbench_delta.dashboard.auth import get_current_principal
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.dashboard.schemas import Principal


def _client(results_dir: Path) -> TestClient:
    app = create_app()
    repo = ExperimentRepository(
        results_dir=results_dir,
        sqlite_path=results_dir.parent / "unused.db",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_current_principal] = lambda: Principal()
    return TestClient(app)


def test_overview_and_leaderboard(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    ov = client.get("/dashboard/api/overview")
    assert ov.status_code == 200
    assert ov.json()["experiment_count"] == 1
    lb = client.get(
        "/dashboard/api/leaderboard",
        params={"sort": "overall_score", "order": "desc"},
    )
    assert lb.status_code == 200
    body = lb.json()
    assert body["total"] == 2
    assert body["items"][0]["agent_id"] == "codex"
    assert body["items"][0]["overall_score"] >= body["items"][1]["overall_score"]


def test_filter_leaderboard_by_agent(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    lb = client.get("/dashboard/api/leaderboard", params={"agent_id": "minicpm"})
    assert lb.status_code == 200
    assert lb.json()["total"] == 1
    assert lb.json()["items"][0]["agent_id"] == "minicpm"


def test_experiments_pagination(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    resp = client.get("/dashboard/api/experiments", params={"page": 1, "page_size": 1})
    assert resp.status_code == 200
    assert resp.json()["page_size"] == 1
    assert len(resp.json()["items"]) == 1


def test_charts_and_correlation(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    radar = client.get("/dashboard/api/charts/radar")
    assert radar.status_code == 200
    assert "data" in radar.json()
    corr = client.get("/dashboard/api/metrics/correlation")
    assert corr.status_code == 200
    assert len(corr.json()["metrics"]) == 18


def test_trajectory_endpoint(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    unit = "gb-repository-search-001::codex::0"
    resp = client.get(f"/dashboard/api/experiments/exp_test001/trajectories/{unit}")
    assert resp.status_code == 200
    assert resp.json()["final_output"]


def test_ws_status_stub(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    resp = client.get("/dashboard/api/ws/status")
    assert resp.status_code == 200
    assert resp.json()["websocket_enabled"] is False


def test_html_pages(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    for path in (
        "/dashboard/",
        "/dashboard/leaderboard",
        "/dashboard/agents",
        "/dashboard/tasks",
        "/dashboard/metrics",
        "/dashboard/trajectories",
        "/dashboard/settings",
        "/dashboard/experiments/exp_test001",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert "text/html" in resp.headers["content-type"]


def test_dashboard_health(sample_experiment_dir: Path) -> None:
    client = _client(sample_experiment_dir)
    assert client.get("/dashboard/health").json()["status"] == "ok"
