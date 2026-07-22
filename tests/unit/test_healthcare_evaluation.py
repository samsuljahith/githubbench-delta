"""Unit tests for the additive Healthcare Evaluation Layer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.healthcare_evaluation.completeness import evaluate_completeness
from githubbench_delta.healthcare_evaluation.critical_findings import evaluate_critical_findings
from githubbench_delta.healthcare_evaluation.engine import evaluate_healthcare
from githubbench_delta.healthcare_evaluation.models import (
    REQUIRED_RGA_FIELDS,
    ClinicalOutput,
    HealthcareEvaluateRequest,
    ReviewStatus,
)
from githubbench_delta.healthcare_evaluation.safety_rules import evaluate_safety_rules
from githubbench_delta.healthcare_evaluation.store import load_report, save_report


@pytest.fixture()
def healthcare_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    results = tmp_path / "results"
    results.mkdir()

    class _Pipe:
        results_dir = str(results)

    class _Runtime:
        pipeline = _Pipe()

    class _Cfg:
        runtime = _Runtime()

    monkeypatch.setattr(
        "githubbench_delta.healthcare_evaluation.store.load_config",
        lambda: _Cfg(),
    )
    return results


def _full_fields() -> dict:
    return {k: f"value for {k}" for k in REQUIRED_RGA_FIELDS}


def test_empty_evidence_insufficient_data(healthcare_tmpdir: Path) -> None:
    report = evaluate_healthcare(HealthcareEvaluateRequest())
    assert report.insufficient_data is True
    assert report.detail and "insufficient_data" in report.detail
    assert load_report(report.report_id) is not None


def test_completeness_full_fields() -> None:
    clinical = ClinicalOutput(fields=_full_fields())
    result = evaluate_completeness(clinical)
    assert result is not None
    assert result.completeness_ratio == 1.0
    assert result.missing_fields == []
    assert set(result.present_fields) == set(REQUIRED_RGA_FIELDS)


def test_completeness_partial_fields() -> None:
    clinical = ClinicalOutput(fields={"chief_complaint": "fatigue", "medications": ["x"]})
    result = evaluate_completeness(clinical)
    assert result is not None
    assert "chief_complaint" in result.present_fields
    assert "falls_history" in result.missing_fields
    assert result.completeness_ratio is not None
    assert result.completeness_ratio < 1.0


def test_completeness_none_without_evidence() -> None:
    assert evaluate_completeness(None) is None
    assert evaluate_completeness(ClinicalOutput()) is None


def test_critical_findings_falls_without_field() -> None:
    clinical = ClinicalOutput(
        fields={"chief_complaint": "tired"},
        narrative="Patient fell twice last month.",
    )
    findings = evaluate_critical_findings(clinical)
    assert any(f.finding_id == "missing_structured_falls" for f in findings)


def test_critical_findings_none_when_field_present() -> None:
    clinical = ClinicalOutput(
        fields={"falls_history": "Two falls in past month"},
        narrative="Patient fell twice last month.",
    )
    findings = evaluate_critical_findings(clinical)
    assert not any(f.finding_id == "missing_structured_falls" for f in findings)


def test_safety_rules_high_risk_med_warning() -> None:
    clinical = ClinicalOutput(
        fields={"medications": "warfarin 5mg"},
        narrative="On warfarin.",
    )
    warnings = evaluate_safety_rules(clinical)
    assert any(w.rule_id == "high_risk_med_without_review_note" for w in warnings)


def test_safety_no_fabricated_score(healthcare_tmpdir: Path) -> None:
    report = evaluate_healthcare(
        HealthcareEvaluateRequest(
            clinical_output=ClinicalOutput(
                fields={"medications": "insulin"},
                narrative="Uses insulin daily.",
            )
        )
    )
    assert report.insufficient_data is False
    assert report.completeness is not None
    # Warnings are qualitative — no clinical "score" field invented
    assert not hasattr(report, "clinical_score")
    assert all(isinstance(w.message, str) for w in report.safety_warnings)


def test_store_round_trip(healthcare_tmpdir: Path) -> None:
    report = evaluate_healthcare(
        HealthcareEvaluateRequest(
            clinical_output=ClinicalOutput(fields=_full_fields()),
            review_status=ReviewStatus.APPROVED,
        )
    )
    loaded = load_report(report.report_id)
    assert loaded is not None
    assert loaded.report_id == report.report_id
    assert loaded.review_status == ReviewStatus.APPROVED
    assert loaded.completeness is not None
    assert loaded.completeness.completeness_ratio == 1.0


def test_api_evaluate_and_get(healthcare_tmpdir: Path) -> None:
    client = TestClient(create_app())
    empty = client.post("/healthcare/evaluate", json={})
    assert empty.status_code == 200
    body = empty.json()
    assert body["ok"] is False
    assert body["status"] == "insufficient_data"

    full = client.post(
        "/healthcare/evaluate",
        json={
            "clinical_output": {"fields": _full_fields()},
            "review_status": "pending",
        },
    )
    assert full.status_code == 200
    data = full.json()
    assert data["ok"] is True
    assert data["status"] == "ok"
    report_id = data["data"]["report_id"]

    got = client.get(f"/healthcare/report/{report_id}")
    assert got.status_code == 200
    assert got.json()["ok"] is True
    assert got.json()["data"]["report"]["completeness"]["completeness_ratio"] == 1.0

    missing = client.get("/healthcare/report/does_not_exist_xyz")
    assert missing.status_code == 200
    assert missing.json()["status"] == "insufficient_data"


def test_engine_bumps_needs_review_on_safety(healthcare_tmpdir: Path) -> None:
    report = evaluate_healthcare(
        HealthcareEvaluateRequest(
            clinical_output=ClinicalOutput(
                fields={"chief_complaint": "check-in"},
                narrative="Patient fell yesterday. On warfarin.",
            )
        )
    )
    assert report.review_status == ReviewStatus.NEEDS_REVIEW
    assert report.safety_warnings or report.critical_findings
