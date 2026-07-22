"""Tests for the ElderWise integration facade APIs."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app

ROOT = Path(__file__).resolve().parents[2]
LIVE_EXP = "exp_6afa2ce533ba4e0a"


def _client() -> TestClient:
    return TestClient(create_app())


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_evaluate_live_experiment():
    if not (ROOT / "results/experiments" / LIVE_EXP / "evaluation_results.json").is_file():
        return
    r = _client().post("/evaluate", json={"experiment_id": LIVE_EXP})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["status"] == "ok"
    assert body["data"]["metrics"]
    assert all("key" in m and "value" in m for m in body["data"]["metrics"])


def test_assessment_and_trust_live():
    if not (ROOT / "results/experiments" / LIVE_EXP / "evaluation_results.json").is_file():
        return
    client = _client()
    a = client.post("/assessment", json={"experiment_id": LIVE_EXP}).json()
    t = client.post("/trust", json={"experiment_id": LIVE_EXP}).json()
    assert a["ok"] and a["data"]["domains"]
    assert t["ok"] and 0 <= t["data"]["overall"] <= 100
    assert t["data"]["breakdown"]


def test_insufficient_data():
    r = _client().post("/evaluate", json={"experiment_id": "exp_does_not_exist_zzz"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["status"] == "insufficient_data"
    assert body["data"] is None


def test_memorization():
    if not (ROOT / "results/experiments" / LIVE_EXP / "evaluation_results.json").is_file():
        return
    r = _client().post("/memorization", json={"experiment_ids": [LIVE_EXP]})
    assert r.status_code == 200
    body = r.json()
    # Proxy mode may still produce breakdowns
    assert body["status"] in ("ok", "insufficient_data")
    assert "data" in body
