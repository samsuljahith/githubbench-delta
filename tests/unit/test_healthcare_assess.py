"""Unit tests for live LLM RGA assess → healthcare evaluate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from githubbench_delta.api.app import create_app
from githubbench_delta.healthcare_evaluation.assess import run_healthcare_assess
from githubbench_delta.healthcare_evaluation.models import REQUIRED_RGA_FIELDS
from githubbench_delta.healthcare_evaluation.rga_extract import (
    LlmEndpoint,
    extract_rga_from_transcript,
    parse_rga_json,
    resolve_llm_endpoint,
)
from githubbench_delta.healthcare_evaluation.store import load_assessment, load_report


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


def _full_json() -> str:
    fields = {k: f"extracted {k}" for k in REQUIRED_RGA_FIELDS}
    return json.dumps({"fields": fields, "narrative": "Full RGA from transcript."})


def _partial_json() -> str:
    return json.dumps(
        {
            "fields": {
                "chief_complaint": "fatigue",
                "medications": ["paracetamol"],
            },
            "narrative": "Partial extraction only.",
        }
    )


def test_parse_rga_omits_empty_and_unknown() -> None:
    clinical = parse_rga_json(
        json.dumps(
            {
                "fields": {
                    "chief_complaint": "pain",
                    "falls_history": "",
                    "invented_field": "nope",
                }
            }
        )
    )
    assert "chief_complaint" in clinical.fields
    assert "falls_history" not in clinical.fields
    assert "invented_field" not in clinical.fields


def test_extract_no_llm_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINICPM_BASE_URL", raising=False)
    monkeypatch.setattr(
        "githubbench_delta.healthcare_evaluation.rga_extract._env_from_config",
        lambda _attr: "",
    )
    assert resolve_llm_endpoint() is None
    result = extract_rga_from_transcript("patient: I feel tired")
    assert result.ok is False
    assert result.detail and "no LLM configured" in result.detail


def test_extract_empty_transcript() -> None:
    result = extract_rga_from_transcript("  ")
    assert result.ok is False
    assert "empty transcript" in (result.detail or "")


def test_assess_incomplete_llm_lower_completeness(healthcare_tmpdir: Path) -> None:
    outcome = run_healthcare_assess(
        transcript="patient: I feel tired. Medications include paracetamol.",
        llm_call=lambda _msgs: _partial_json(),
        extract_fn=lambda transcript, llm_call=None, **_kw: extract_rga_from_transcript(
            transcript,
            llm_call=llm_call,
            endpoint=LlmEndpoint(
                provider="mock",
                api_key="x",
                base_url=None,
                model="mock",
            ),
        ),
    )
    assert outcome.ok is True
    assert outcome.report is not None
    assert outcome.report.completeness is not None
    ratio = outcome.report.completeness.completeness_ratio
    assert ratio is not None
    assert ratio < 1.0
    assert "falls_history" in outcome.report.completeness.missing_fields
    # Must not invent missing domains
    assert "falls_history" not in (outcome.assessment or {}).get("clinical_output", {}).get(
        "fields", {}
    )
    loaded = load_assessment(outcome.assessment["assessment_id"])
    assert loaded is not None
    assert load_report(outcome.report.report_id) is not None


def test_assess_full_rga_completeness_one(healthcare_tmpdir: Path) -> None:
    outcome = run_healthcare_assess(
        transcript="full conversation about all geriatric domains",
        llm_call=lambda _msgs: _full_json(),
        extract_fn=lambda transcript, llm_call=None, **_kw: extract_rga_from_transcript(
            transcript,
            llm_call=llm_call,
            endpoint=LlmEndpoint(
                provider="mock",
                api_key="x",
                base_url=None,
                model="mock",
            ),
        ),
    )
    assert outcome.ok is True
    assert outcome.report is not None
    assert outcome.report.completeness is not None
    assert outcome.report.completeness.completeness_ratio == 1.0
    assert outcome.report.completeness.missing_fields == []


def test_assess_no_transcript_insufficient(healthcare_tmpdir: Path) -> None:
    outcome = run_healthcare_assess(transcript="", conversation=[])
    assert outcome.ok is False
    assert outcome.detail and "no conversation transcript" in outcome.detail


def test_assess_does_not_use_patient_chrome_as_fields(healthcare_tmpdir: Path) -> None:
    """Patient chrome must not become clinical_output fields."""

    outcome = run_healthcare_assess(
        patient={
            "id": "p1",
            "chief_complaint": "SHOULD_NOT_APPEAR_AS_FIELD",
            "medications": ["warfarin"],
        },
        transcript="clinician: how are you?\npatient: Fine, no issues.",
        llm_call=lambda _msgs: json.dumps(
            {"fields": {"mood": "stable"}, "narrative": "Brief check-in."}
        ),
        extract_fn=lambda transcript, llm_call=None, **_kw: extract_rga_from_transcript(
            transcript,
            llm_call=llm_call,
            endpoint=LlmEndpoint(
                provider="mock",
                api_key="x",
                base_url=None,
                model="mock",
            ),
        ),
    )
    assert outcome.ok is True
    fields = (outcome.assessment or {}).get("clinical_output", {}).get("fields", {})
    assert fields == {"mood": "stable"}
    assert "SHOULD_NOT_APPEAR_AS_FIELD" not in str(fields)


def test_api_assess_with_mocked_extract(
    healthcare_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_extract(transcript, llm_call=None, **_kw):
        return extract_rga_from_transcript(
            transcript,
            llm_call=lambda _m: _partial_json(),
            endpoint=LlmEndpoint(
                provider="mock",
                api_key="x",
                base_url=None,
                model="mock",
            ),
        )

    monkeypatch.setattr(
        "githubbench_delta.healthcare_evaluation.assess.extract_rga_from_transcript",
        _fake_extract,
    )
    client = TestClient(create_app())
    empty = client.post("/healthcare/assess", json={})
    assert empty.status_code == 200
    assert empty.json()["status"] == "insufficient_data"

    ok = client.post(
        "/healthcare/assess",
        json={
            "transcript": "patient: tired; meds paracetamol",
            "patient": {"id": "syn-1"},
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] is True
    report_id = body["data"]["report_id"]
    got = client.get(f"/healthcare/report/{report_id}")
    assert got.status_code == 200
    assert got.json()["ok"] is True
    ratio = got.json()["data"]["report"]["completeness"]["completeness_ratio"]
    assert ratio < 1.0
