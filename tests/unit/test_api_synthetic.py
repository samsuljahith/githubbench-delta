"""Tests for Gemini synthetic generation + hardened case runs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.api.synthetic import GeneratedPatient, generate_patients_envelope
from githubbench_delta.api.synthetic import GeneratePatientsRequest

ROOT = Path(__file__).resolve().parents[2]
LIVE_EXP = "exp_6afa2ce533ba4e0a"
PATIENT = {
    "id": "SYN-TEST-LOOP",
    "name": "Test Patient",
    "age": 80,
    "sex": "F",
    "chief_complaint": "Falls",
}


def _client() -> TestClient:
    return TestClient(create_app())


def test_generate_patients_missing_key(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from githubbench_delta.core.config import load_config

    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    with (
        patch("githubbench_delta.api.synthetic.load_config", return_value=cfg),
        patch("githubbench_delta.api.synthetic._gemini_api_key", return_value=""),
    ):
        body = _client().post("/cases/generate-patients", json={"count": 2}).json()
    assert body["ok"] is False
    assert body["status"] == "insufficient_data"
    assert "GEMINI_API_KEY" in (body["detail"] or "")


def test_generate_patients_mocked(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from githubbench_delta.core.config import load_config

    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"

    def fake_gemini(*, count: int, client=None):
        return [
            GeneratedPatient(
                id=f"SYN-G-{i}",
                name=f"Patient {i}",
                age=70 + i,
                sex="F" if i % 2 == 0 else "M",
                chief_complaint="Fatigue",
                comorbidities=["Hypertension"],
                medications=["Amlodipine"],
                living_situation="Lives alone",
                risk_profile="Moderate",
            )
            for i in range(count)
        ]

    with patch("githubbench_delta.api.synthetic.load_config", return_value=cfg):
        env = generate_patients_envelope(
            GeneratePatientsRequest(count=3),
            gemini_fn=fake_gemini,
        )
    assert env.ok is True
    assert env.data is not None
    assert len(env.data["patients"]) == 3
    assert env.data["source"] == "gemini"
    batch = env.data["batch_id"]
    path = tmp_path / "synthetic" / f"{batch}.json"
    assert path.is_file()


def test_generate_patients_http_route(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from githubbench_delta.core.config import load_config

    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"

    def fake_gemini(*, count: int, client=None):
        return [
            GeneratedPatient(
                id="SYN-G-http",
                name="Ada",
                age=81,
                sex="F",
                chief_complaint="Falls",
                comorbidities=[],
                medications=[],
                living_situation="Alone",
                risk_profile="High",
            )
        ]

    with (
        patch("githubbench_delta.api.synthetic.load_config", return_value=cfg),
        patch(
            "githubbench_delta.api.synthetic.call_gemini_generate_patients",
            side_effect=fake_gemini,
        ),
    ):
        body = _client().post("/cases/generate-patients", json={"count": 1}).json()
    assert body["ok"] is True
    assert body["data"]["patients"][0]["id"] == "SYN-G-http"


def test_cases_run_failed_agent_no_cache(tmp_path: Path, monkeypatch):
    """Failed agent runs must return insufficient_data and not write cache."""

    monkeypatch.setenv("GITHUBBENCH_CASE_DRY_RUN", "true")
    monkeypatch.setenv("GITHUBBENCH_CASE_DATASET", str(ROOT / "datasets" / "v1"))
    cases_dir = tmp_path / "cases"
    failed_exp = "exp_26e025d5824e44f6"
    failed_path = ROOT / "results/experiments" / failed_exp / "evaluation_results.json"
    if not failed_path.is_file():
        return

    with (
        patch("githubbench_delta.api.cases._cases_dir", return_value=cases_dir),
        patch("githubbench_delta.api.cases.ExperimentRunner") as runner_cls,
    ):
        runner = runner_cls.return_value
        manifest = AsyncMock()
        manifest.experiment_id = failed_exp
        runner.run = AsyncMock(return_value=manifest)

        body = _client().post(
            "/cases/run",
            json={"patient": PATIENT, "agent_id": "minicpm", "force": True},
        ).json()
        assert body["ok"] is False
        assert body["status"] == "insufficient_data"
        assert "Connection" in (body["detail"] or "") or "Provider" in (body["detail"] or "")
        assert not list(cases_dir.glob("*.json"))


def test_cases_run_success_includes_loop_engineering(tmp_path: Path, monkeypatch):
    live = ROOT / "results/experiments" / LIVE_EXP / "evaluation_results.json"
    if not live.is_file():
        return
    monkeypatch.setenv("GITHUBBENCH_CASE_DATASET", str(ROOT / "datasets" / "v1"))
    cases_dir = tmp_path / "cases"

    # Build a tiny successful inspect by patching _inspect_agent_run
    with (
        patch("githubbench_delta.api.cases._cases_dir", return_value=cases_dir),
        patch("githubbench_delta.api.cases.ExperimentRunner") as runner_cls,
        patch(
            "githubbench_delta.api.cases._inspect_agent_run",
            return_value={
                "success": True,
                "error": None,
                "step_count": 4,
                "tool_call_count": 2,
                "error_count": 0,
                "latency_ms": 120.0,
            },
        ),
    ):
        runner = runner_cls.return_value
        manifest = AsyncMock()
        manifest.experiment_id = LIVE_EXP
        runner.run = AsyncMock(return_value=manifest)
        body = _client().post(
            "/cases/run",
            json={"patient": PATIENT, "agent_id": "codex", "force": True},
        ).json()
        assert body["ok"] is True
        le = body["data"]["loop_engineering"]
        assert le["step_count"] == 4
        assert le["tool_call_count"] == 2
        assert "trajectory steps" in le["summary"]
        cache_files = list(cases_dir.glob("*.json"))
        assert len(cache_files) == 1
