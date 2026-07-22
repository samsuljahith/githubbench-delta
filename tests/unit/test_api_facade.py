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
    # Live artifacts include MetricResult.reasoning — facade must surface it.
    with_reason = [m for m in body["data"]["metrics"] if m.get("reasoning")]
    assert with_reason, "expected at least one metric with deterministic reasoning"


def test_build_evaluate_attaches_latest_reasoning(monkeypatch):
    """Scores mean-average; reasoning comes from the latest metric_results row."""

    from githubbench_delta.api import facade as facade_mod

    class FakeRepo:
        def load_evaluations_raw(self, experiment_id: str):
            assert experiment_id == "exp_fake"
            return [
                {
                    "agent_id": "codex",
                    "evaluation": {
                        "metadata": {
                            "weighted_scores": [
                                {"metric_id": "tool_economy", "score": 0.5, "skipped": False},
                            ]
                        },
                        "metric_results": {
                            "tool_economy": {
                                "metric_id": "tool_economy",
                                "score": 0.5,
                                "reasoning": "first row reason",
                                "suggested_improvements": ["use fewer tools"],
                            }
                        },
                    },
                },
                {
                    "agent_id": "codex",
                    "evaluation": {
                        "metadata": {
                            "weighted_scores": [
                                {"metric_id": "tool_economy", "score": 0.7, "skipped": False},
                            ]
                        },
                        "metric_results": {
                            "tool_economy": {
                                "metric_id": "tool_economy",
                                "score": 0.7,
                                "reasoning": "latest row reason",
                                "evidence": {"tool_calls": 2},
                                "suggested_improvements": ["plan before tools"],
                            }
                        },
                    },
                },
            ]

    monkeypatch.setattr(facade_mod, "_repo", lambda: FakeRepo())
    env = facade_mod.build_evaluate("exp_fake", agent_id="codex")
    assert env.ok is True
    metrics = env.data["metrics"]
    assert len(metrics) == 1
    m = metrics[0]
    assert m["key"] == "tool_economy"
    assert m["value"] == 60.0  # mean of 0.5 and 0.7
    assert m["reasoning"] == "latest row reason"
    assert m["evidence"] == {"tool_calls": 2}
    assert m["suggested_improvements"] == ["plan before tools"]
    assert "see reasoning" in m["description"]


def test_loop_engineering_includes_all_metrics():
    from githubbench_delta.api.cases import _loop_engineering

    le = _loop_engineering(
        inspect={
            "step_count": 3,
            "tool_call_count": 2,
            "error_count": 1,
            "latency_ms": 50.0,
        },
        evaluate_data={
            "metrics": [
                {
                    "key": "tool_economy",
                    "label": "Tool Economy",
                    "value": 55.0,
                    "unit": "%",
                    "reasoning": "two tools for one file",
                },
                {
                    "key": "blast_radius",
                    "label": "Blast Radius",
                    "value": 80.0,
                    "unit": "%",
                    "reasoning": "no files outside set",
                },
                {"key": "task_resolution", "label": "Task Resolution", "value": 40.0, "unit": "%"},
            ]
        },
    )
    assert le["step_count"] == 3
    related = le["related_metrics"]
    assert len(related) == 3
    assert {r["key"] for r in related} == {
        "tool_economy",
        "blast_radius",
        "task_resolution",
    }
    assert related[0]["reasoning"] == "two tools for one file"
    assert "reasoning" not in related[2]


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
