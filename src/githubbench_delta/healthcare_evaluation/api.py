"""REST API for the additive Healthcare Evaluation Layer."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from githubbench_delta.healthcare_evaluation.assess import run_healthcare_assess
from githubbench_delta.healthcare_evaluation.engine import evaluate_healthcare
from githubbench_delta.healthcare_evaluation.models import (
    HealthcareAssessRequest,
    HealthcareEvaluateRequest,
)
from githubbench_delta.healthcare_evaluation.store import load_report

healthcare_router = APIRouter(tags=["healthcare"])

StatusLiteral = Literal["ok", "insufficient_data"]


class HealthcareEnvelope(BaseModel):
    ok: bool
    status: StatusLiteral
    detail: str | None = None
    data: dict[str, Any] | None = None


@healthcare_router.post("/healthcare/evaluate", response_model=HealthcareEnvelope)
def post_healthcare_evaluate(body: HealthcareEvaluateRequest) -> HealthcareEnvelope:
    """Evaluate submitted clinical / RGA evidence (rule-based). Never fabricates scores."""

    report = evaluate_healthcare(body)
    if report.insufficient_data:
        return HealthcareEnvelope(
            ok=False,
            status="insufficient_data",
            detail=report.detail,
            data={"report_id": report.report_id, "report": report.model_dump()},
        )
    return HealthcareEnvelope(
        ok=True,
        status="ok",
        detail=None,
        data={"report_id": report.report_id, "report": report.model_dump()},
    )


@healthcare_router.post("/healthcare/assess", response_model=HealthcareEnvelope)
def post_healthcare_assess(body: HealthcareAssessRequest) -> HealthcareEnvelope:
    """
    Live LLM RGA extraction from conversation, then rule-based evaluate.

    Uses only the newly generated structured assessment — never patient-chrome placeholders.
    """

    turns = None
    if body.conversation:
        turns = [t.model_dump() for t in body.conversation]
    outcome = run_healthcare_assess(
        patient=body.patient,
        transcript=body.transcript,
        conversation=turns,
    )
    if not outcome.ok or outcome.report is None:
        data: dict[str, Any] | None = None
        if outcome.assessment is not None:
            data = {
                "assessment_id": outcome.assessment.get("assessment_id"),
                "assessment": outcome.assessment,
                "report_id": outcome.assessment.get("report_id"),
                "report": outcome.report.model_dump() if outcome.report else None,
            }
        return HealthcareEnvelope(
            ok=False,
            status="insufficient_data",
            detail=outcome.detail,
            data=data,
        )

    assert outcome.report is not None and outcome.assessment is not None
    return HealthcareEnvelope(
        ok=True,
        status="ok",
        detail=None,
        data={
            "assessment_id": outcome.assessment.get("assessment_id"),
            "report_id": outcome.report.report_id,
            "assessment": outcome.assessment,
            "report": outcome.report.model_dump(),
        },
    )


@healthcare_router.get("/healthcare/report/{report_id}", response_model=HealthcareEnvelope)
def get_healthcare_report(report_id: str) -> HealthcareEnvelope:
    """Load a previously stored healthcare evaluation report."""

    report = load_report(report_id)
    if report is None:
        return HealthcareEnvelope(
            ok=False,
            status="insufficient_data",
            detail=f"insufficient_data: healthcare report '{report_id}' not found",
            data=None,
        )
    if report.insufficient_data:
        return HealthcareEnvelope(
            ok=False,
            status="insufficient_data",
            detail=report.detail,
            data={"report_id": report.report_id, "report": report.model_dump()},
        )
    return HealthcareEnvelope(
        ok=True,
        status="ok",
        detail=None,
        data={"report_id": report.report_id, "report": report.model_dump()},
    )
