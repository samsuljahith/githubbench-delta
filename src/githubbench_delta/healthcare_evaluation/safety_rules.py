"""Clinical Safety Rules — warnings only; never diagnoses."""

from __future__ import annotations

import re

from githubbench_delta.healthcare_evaluation.models import (
    ClinicalOutput,
    SafetyWarning,
    combined_text,
    field_has_value,
)

_HIGH_RISK_MEDS = (
    r"\bwarfarin\b",
    r"\binsulin\b",
    r"\bdigoxin\b",
    r"\bopioid",
    r"\bmorphine\b",
    r"\boxycodone\b",
    r"\bbenzodiazep",
    r"\bdiazepam\b",
    r"\blorazepam\b",
    r"\banticholinergic\b",
)

_MITIGATION_CUES = (
    r"\breview(ed)?\b",
    r"\bmonitor",
    r"\bfollow[- ]?up\b",
    r"\bdeprescrib",
    r"\breconciled\b",
    r"\bsafety\s+plan\b",
    r"\bpt\s+educat",
)


def evaluate_safety_rules(
    clinical: ClinicalOutput | None,
    *,
    transcript: str | None = None,
) -> list[SafetyWarning]:
    """Emit rule-based safety warnings; does not score or diagnose."""

    text = combined_text(clinical, transcript)
    if not text.strip() and not (clinical and clinical.fields):
        return []

    warnings: list[SafetyWarning] = []
    lower = text.lower()
    fields = (clinical.fields if clinical else {}) or {}

    # Falls mentioned without mitigation language.
    if re.search(r"\bfell\b|\bfalls?\b|\bfalling\b", lower):
        if not any(re.search(p, lower) for p in _MITIGATION_CUES):
            if not field_has_value(fields.get("risk_flags")):
                warnings.append(
                    SafetyWarning(
                        rule_id="falls_without_mitigation_note",
                        message=(
                            "Falls-related language present without documented mitigation, "
                            "follow-up, or risk_flags — clinician review recommended."
                        ),
                        evidence_span="falls",
                    )
                )

    # High-risk med keywords without follow-up / review note.
    med_hit: str | None = None
    for pat in _HIGH_RISK_MEDS:
        m = re.search(pat, lower)
        if m:
            med_hit = m.group(0)
            break
    if med_hit and not any(re.search(p, lower) for p in _MITIGATION_CUES):
        warnings.append(
            SafetyWarning(
                rule_id="high_risk_med_without_review_note",
                message=(
                    f"High-risk medication cue '{med_hit}' without explicit review/monitoring "
                    "language — warning only, not a diagnosis."
                ),
                evidence_span=med_hit,
            )
        )

    # Polypharmacy / multiple meds listed but medications field empty.
    if re.search(r"\bpolypharmacy\b|\bmultiple\s+medications\b", lower):
        if not field_has_value(fields.get("medications")):
            warnings.append(
                SafetyWarning(
                    rule_id="polypharmacy_without_med_list",
                    message=(
                        "Polypharmacy language present but structured medications list is empty."
                    ),
                    evidence_span="polypharmacy",
                )
            )

    # Cognition concern without structured cognition field (if not already covered).
    if re.search(r"\bconfused\b|\bdementia\b|\bdisorient", lower):
        if not field_has_value(fields.get("cognition")):
            warnings.append(
                SafetyWarning(
                    rule_id="cognition_cue_without_structured_field",
                    message=(
                        "Cognition-related language without structured cognition field — "
                        "incomplete documentation warning."
                    ),
                    evidence_span="cognition",
                )
            )

    return warnings
