"""Orchestrate LLM RGA assess → persist → rule-based healthcare evaluate."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from githubbench_delta.healthcare_evaluation.engine import evaluate_healthcare
from githubbench_delta.healthcare_evaluation.models import (
    ClinicalOutput,
    HealthcareEvaluateRequest,
    HealthcareReport,
    utc_now_iso,
)
from githubbench_delta.healthcare_evaluation.rga_extract import (
    ExtractResult,
    extract_rga_from_transcript,
)
from githubbench_delta.healthcare_evaluation.store import save_assessment


def _transcript_from_conversation(conversation: list[dict[str, Any]] | None) -> str:
    if not conversation:
        return ""
    lines: list[str] = []
    for turn in conversation:
        role = str(turn.get("role") or "speaker").strip()
        text = str(turn.get("text") or turn.get("content") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


class AssessOutcome:
    def __init__(
        self,
        *,
        ok: bool,
        detail: str | None,
        assessment: dict[str, Any] | None,
        report: HealthcareReport | None,
    ) -> None:
        self.ok = ok
        self.detail = detail
        self.assessment = assessment
        self.report = report


def run_healthcare_assess(
    *,
    patient: dict[str, Any] | None = None,
    transcript: str | None = None,
    conversation: list[dict[str, Any]] | None = None,
    llm_call: Callable[[list[dict[str, str]]], str] | None = None,
    extract_fn: Callable[..., ExtractResult] | None = None,
) -> AssessOutcome:
    """
    Live LLM RGA extraction then rule-based evaluate.

    Uses ONLY the LLM clinical_output for evaluate — never merges patient chrome fields.
    """

    combined = (transcript or "").strip()
    if not combined:
        combined = _transcript_from_conversation(conversation)
    if not combined.strip():
        return AssessOutcome(
            ok=False,
            detail="insufficient_data: no conversation transcript provided for RGA assess",
            assessment=None,
            report=None,
        )

    extract = (extract_fn or extract_rga_from_transcript)(
        combined,
        llm_call=llm_call,
    )
    assessment_id = f"rga_{uuid.uuid4().hex[:12]}"
    assessment: dict[str, Any] = {
        "assessment_id": assessment_id,
        "created_at": utc_now_iso(),
        "patient": patient,
        "transcript": combined,
        "provider": extract.provider,
        "model": extract.model,
        "raw_text": extract.raw_text,
        "clinical_output": extract.clinical_output.model_dump(),
        "ok": extract.ok,
        "detail": extract.detail,
        "provenance": (
            "Live LLM RGA extraction from conversation — not Gemini chrome placeholders; "
            "not GitHubBench engineering metrics."
        ),
    }
    save_assessment(assessment)

    if not extract.ok:
        return AssessOutcome(
            ok=False,
            detail=extract.detail,
            assessment=assessment,
            report=None,
        )

    # Evaluate using ONLY LLM structured output (no transcript re-injection for completeness
    # chrome gaming — findings/safety may still use narrative inside clinical_output).
    report = evaluate_healthcare(
        HealthcareEvaluateRequest(
            patient=patient,
            clinical_output=ClinicalOutput(
                fields=dict(extract.clinical_output.fields or {}),
                narrative=extract.clinical_output.narrative,
            ),
            transcript=None,
        )
    )
    assessment["report_id"] = report.report_id
    save_assessment(assessment)

    if report.insufficient_data:
        return AssessOutcome(
            ok=False,
            detail=report.detail,
            assessment=assessment,
            report=report,
        )

    return AssessOutcome(
        ok=True,
        detail=None,
        assessment=assessment,
        report=report,
    )
