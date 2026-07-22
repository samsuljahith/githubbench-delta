"""Tests for versioned synthetic patient fixtures."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.api.cases import SCENARIO_TYPES, load_synthetic_fixtures

REQUIRED = {
    "complete",
    "missing_finding",
    "hallucination_risk",
    "contraindication",
    "incomplete",
}


def test_synthetic_fixtures_one_of_each_scenario() -> None:
    fixtures = load_synthetic_fixtures()
    assert len(fixtures) == 5
    types = {str(f.get("scenario_type")) for f in fixtures}
    assert types == REQUIRED
    for fx in fixtures:
        assert fx.get("id")
        assert fx.get("conversation") or fx.get("conversation_text")
        text = fx.get("conversation_text") or ""
        if not text and fx.get("conversation"):
            text = " ".join(t.get("text", "") for t in fx["conversation"])
        words = len(text.split())
        assert 100 <= words <= 400, f"{fx.get('id')} word count {words}"


def test_fixture_patients_api() -> None:
    client = TestClient(create_app())
    res = client.get("/cases/fixture-patients")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["data"]["count"] == 5
    types = {p["scenario_type"] for p in body["data"]["patients"]}
    assert types == REQUIRED


def test_fixture_files_named_by_scenario(tmp_path: Path) -> None:  # noqa: ARG001
    root = Path("datasets/synthetic")
    for name in [
        "patient_siti_rohana_complete.json",
        "patient_lim_wei_ming_missing_finding.json",
        "patient_patricia_ong_hallucination_risk.json",
        "patient_harold_benedict_contraindication.json",
        "patient_mei_ling_tan_incomplete.json",
    ]:
        assert (root / name).is_file()
    assert frozenset(REQUIRED) == SCENARIO_TYPES
