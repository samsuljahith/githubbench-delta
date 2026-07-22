"""Models for the Healthcare Evaluation Layer."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


# Rapid Geriatric Assessment–style fields expected for completeness checks.
REQUIRED_RGA_FIELDS: tuple[str, ...] = (
    "chief_complaint",
    "falls_history",
    "weight_change",
    "medications",
    "cognition",
    "mood",
    "mobility",
    "adls_iadls",
    "living_situation",
    "social_support",
    "comorbidities",
    "risk_flags",
)


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"


class ClinicalOutput(BaseModel):
    """Structured clinical / RGA extraction supplied by the caller."""

    fields: dict[str, Any] = Field(default_factory=dict)
    narrative: str | None = None


class CompletenessResult(BaseModel):
    present_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    completeness_ratio: float | None = None
    detail: str | None = None


class CriticalFinding(BaseModel):
    finding_id: str
    severity: Literal["warning", "info"]
    evidence_span: str
    message: str


class SafetyWarning(BaseModel):
    rule_id: str
    message: str
    evidence_span: str | None = None


class HealthcareEvaluateRequest(BaseModel):
    """Request body for POST /healthcare/evaluate."""

    patient: dict[str, Any] | None = None
    clinical_output: ClinicalOutput | None = None
    transcript: str | None = None
    review_status: ReviewStatus | None = None
    report_id: str | None = None


class ConversationTurn(BaseModel):
    role: str | None = None
    text: str | None = None
    content: str | None = None
    t: str | None = None


class HealthcareAssessRequest(BaseModel):
    """Request body for POST /healthcare/assess — live LLM RGA then evaluate."""

    patient: dict[str, Any] | None = None
    transcript: str | None = None
    conversation: list[ConversationTurn] | None = None


class HealthcareReport(BaseModel):
    report_id: str
    created_at: str
    review_status: ReviewStatus = ReviewStatus.PENDING
    patient: dict[str, Any] | None = None
    completeness: CompletenessResult | None = None
    critical_findings: list[CriticalFinding] = Field(default_factory=list)
    safety_warnings: list[SafetyWarning] = Field(default_factory=list)
    provenance: str = (
        "Healthcare Evaluation Layer — rule-based checks on submitted clinical "
        "evidence only. Not a diagnosis. Separate from GitHubBench 18 engineering metrics."
    )
    insufficient_data: bool = False
    detail: str | None = None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def field_has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def combined_text(clinical: ClinicalOutput | None, transcript: str | None) -> str:
    parts: list[str] = []
    if clinical:
        if clinical.narrative and clinical.narrative.strip():
            parts.append(clinical.narrative.strip())
        for key, val in (clinical.fields or {}).items():
            if field_has_value(val):
                if isinstance(val, list):
                    parts.append(f"{key}: {', '.join(str(x) for x in val)}")
                else:
                    parts.append(f"{key}: {val}")
    if transcript and transcript.strip():
        parts.append(transcript.strip())
    return "\n".join(parts)
