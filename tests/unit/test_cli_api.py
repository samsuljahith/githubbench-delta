"""CLI and FastAPI smoke tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from githubbench_delta.api.app import create_app
from githubbench_delta.cli import app as cli_app
from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs"
runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(cli_app, ["version"])
    assert result.exit_code == 0
    assert "githubbench-delta" in result.stdout


def test_cli_list_metrics() -> None:
    result = runner.invoke(cli_app, ["list", "metrics", "--config-dir", str(CONFIG_DIR)])
    assert result.exit_code == 0, result.stdout
    assert "task_resolution" in result.stdout
    assert "local_vs_hosted_parity" in result.stdout
    assert "Total: 18" in result.stdout
    assert "exact_match" not in result.stdout


def test_cli_list_agents_and_tasks() -> None:
    agents = runner.invoke(cli_app, ["list", "agents"])
    tasks = runner.invoke(cli_app, ["list", "tasks"])
    assert agents.exit_code == 0
    assert tasks.exit_code == 0
    assert "minicpm" in agents.stdout
    assert "bug_fix" in tasks.stdout


def test_api_health_and_catalog(monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    catalog = client.get("/metrics/catalog")
    assert catalog.status_code == 200
    rows = catalog.json()
    assert len(rows) == 18
    assert {row["id"] for row in rows} == set(METHODOLOGY_METRIC_IDS)

    dash = client.get("/dashboard/health")
    assert dash.status_code == 200
