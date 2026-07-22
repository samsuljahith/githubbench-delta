"""Orchestrate healthcare evaluation → HealthcareReport."""

from __future__ import annotations

import uuid

from githubbench_delta.healthcare_evaluation.completeness import evaluate_completeness
from githubbench_delta.healthcare_evaluation.critical_findings import evaluate_critical_findings
from githubbench_delta.healthcare_evaluation.models import (
    HealthcareEvaluateRequest,
    HealthcareReport,
    utc_now_iso,
)
from githubbench_delta.healthcare_evaluation.review import resolve_review_status
from githubbench_delta.healthcare_evaluation.safety_rules import evaluate_safety_rules
from githubbench_delta.healthcare_evaluation.store import save_report


def evaluate_healthcare(request: HealthcareEvaluateRequest) -> HealthcareReport:
    """
    Run rule-based clinical checks on submitted evidence.

    Returns a report with insufficient_data=True when no clinical evidence is present.
    Does not invent scores or diagnoses.
    """

    report_id = (request.report_id or "").strip() or f"hc_{uuid.uuid4().hex[:12]}"
    review = resolve_review_status(request.review_status)

    completeness = evaluate_completeness(
        request.clinical_output,
        transcript=request.transcript,
    )
    if completeness is None:
        report = HealthcareReport(
            report_id=report_id,
            created_at=utc_now_iso(),
            review_status=review,
            patient=request.patient,
            insufficient_data=True,
            detail=(
                "insufficient_data: no clinical_output fields, narrative, or transcript "
                "provided — cannot evaluate completeness, findings, or safety."
            ),
        )
        save_report(report)
        return report

    findings = evaluate_critical_findings(
        request.clinical_output,
        transcript=request.transcript,
    )
    warnings = evaluate_safety_rules(
        request.clinical_output,
        transcript=request.transcript,
    )

    # Auto-suggest needs_review when warnings/findings exist and status still pending.
    if review.value == "pending" and (findings or warnings):
        from githubbench_delta.healthcare_evaluation.models import ReviewStatus

        # Keep pending unless caller set otherwise — do not auto-approve.
        # Optionally bump to needs_review when safety warnings present.
        if warnings:
            review = ReviewStatus.NEEDS_REVIEW

    report = HealthcareReport(
        report_id=report_id,
        created_at=utc_now_iso(),
        review_status=review,
        patient=request.patient,
        completeness=completeness,
        critical_findings=findings,
        safety_warnings=warnings,
        insufficient_data=False,
        detail=None,
    )
    save_report(report)
    return report
