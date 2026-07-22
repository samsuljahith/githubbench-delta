"""Tests for POST /cases/run live patient case evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.api.cases import resolve_case_agent, seed_for_patient, task_id_for_patient
from githubbench_delta.api.facade import FacadeEnvelope

ROOT = Path(__file__).resolve().parents[2]
LIVE_EXP = "exp_6afa2ce533ba4e0a"
PATIENT = {
    "id": "SYN-TEST-0417",
    "name": "Test Patient",
    "age": 80,
    "sex": "F",
    "chief_complaint": "Falls",
}


def _client() -> TestClient:
    return TestClient(create_app())


def test_task_id_for_patient_stable():
    ids = ["a", "b", "c", "d"]
    assert task_id_for_patient("SYN-0417", ids) == task_id_for_patient("SYN-0417", ids)
    assert task_id_for_patient("SYN-0417", ids) != task_id_for_patient("SYN-0418", ids)
    assert seed_for_patient("SYN-0417") == seed_for_patient("SYN-0417")


def test_resolve_case_agent(monkeypatch):
    monkeypatch.setenv("GITHUBBENCH_CASE_AGENT", "minicpm")
    assert resolve_case_agent(None) == "minicpm"
    assert resolve_case_agent("codex") == "codex"
    assert resolve_case_agent("CLAUDE") == "claude"
    assert resolve_case_agent("gemini") is None


def test_get_case_agents():
    r = _client().get("/cases/agents")
    assert r.status_code == 200
    body = r.json()
    ids = {row["id"] for row in body}
    assert ids == {"minicpm", "claude", "codex"}
    assert all("hint" in row and "deployment" in row for row in body)


def test_cases_run_missing_patient_id():
    r = _client().post("/cases/run", json={"patient": {"id": "  "}})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["status"] == "insufficient_data"


def test_cases_run_invalid_agent():
    r = _client().post(
        "/cases/run",
        json={"patient": PATIENT, "agent_id": "gemini", "force": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["status"] == "insufficient_data"
    assert "Invalid agent_id" in (body["detail"] or "")


def test_cases_run_agent_override_and_cache(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITHUBBENCH_CASE_DRY_RUN", "true")
    monkeypatch.setenv("GITHUBBENCH_CASE_AGENT", "minicpm")
    monkeypatch.setenv("GITHUBBENCH_CASE_DATASET", str(ROOT / "datasets" / "v1"))

    cases_dir = tmp_path / "cases"
    results_dir = tmp_path / "experiments"

    from githubbench_delta.core.config import load_config

    cfg = load_config()
    cfg.runtime.pipeline.results_dir = results_dir

    with (
        patch("githubbench_delta.api.cases._cases_dir", return_value=cases_dir),
        patch("githubbench_delta.api.cases.load_config", return_value=cfg),
        patch("githubbench_delta.api.cases.ExperimentRunner") as runner_cls,
    ):
        live_eval = ROOT / "results/experiments" / LIVE_EXP / "evaluation_results.json"
        if not live_eval.is_file():
            return

        runner = runner_cls.return_value
        manifest = AsyncMock()
        manifest.experiment_id = LIVE_EXP
        runner.run = AsyncMock(return_value=manifest)

        client = _client()
        first = client.post(
            "/cases/run",
            json={"patient": PATIENT, "agent_id": "codex", "force": True},
        ).json()
        assert first["ok"] is True
        assert first["data"]["agent_id"] == "codex"
        assert first["data"]["cached"] is False

        # Spec passed to runner must use body agent, not env default
        call_kwargs = runner.run.await_args
        spec = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("spec")
        assert spec is not None
        assert spec.agent_ids == ["codex"]

        cache_file = cases_dir / "SYN-TEST-0417__codex.json"
        assert cache_file.is_file()
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        assert cached["agent_id"] == "codex"

        second = client.post(
            "/cases/run",
            json={"patient": PATIENT, "agent_id": "codex", "force": False},
        ).json()
        assert second["ok"] is True
        assert second["data"]["cached"] is True
        assert runner.run.await_count == 1

        # Different agent → separate cache, new run
        third = client.post(
            "/cases/run",
            json={"patient": PATIENT, "agent_id": "minicpm", "force": False},
        ).json()
        assert third["ok"] is True
        assert third["data"]["cached"] is False
        assert third["data"]["agent_id"] == "minicpm"
        assert (cases_dir / "SYN-TEST-0417__minicpm.json").is_file()
        assert runner.run.await_count == 2


def test_cases_run_runner_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GITHUBBENCH_CASE_DRY_RUN", "true")
    monkeypatch.setenv("GITHUBBENCH_CASE_DATASET", str(ROOT / "datasets" / "v1"))
    cases_dir = tmp_path / "cases"

    with (
        patch("githubbench_delta.api.cases._cases_dir", return_value=cases_dir),
        patch("githubbench_delta.api.cases.ExperimentRunner") as runner_cls,
    ):
        runner = runner_cls.return_value
        runner.run = AsyncMock(side_effect=RuntimeError("provider down"))
        body = (
            _client()
            .post(
                "/cases/run",
                json={"patient": PATIENT, "agent_id": "codex", "force": True},
            )
            .json()
        )
        assert body["ok"] is False
        assert body["status"] == "insufficient_data"
        assert "provider down" in (body["detail"] or "")


def test_envelope_shape_helpers():
    env = FacadeEnvelope(ok=False, status="insufficient_data", detail="x", data=None)
    assert env.ok is False
