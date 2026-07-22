"""Missing Critical Findings — heuristic omission / cue detection (warnings only)."""

from __future__ import annotations

import re

from githubbench_delta.healthcare_evaluation.models import (
    ClinicalOutput,
    CriticalFinding,
    combined_text,
    field_has_value,
)

# Cues in free text that suggest a critical topic was discussed.
_CRITICAL_CUES: dict[str, tuple[str, ...]] = {
    "falls": (
        r"\bfell\b",
        r"\bfalls?\b",
        r"\bfalling\b",
        r"\bsyncope\b",
        r"\bnear[- ]fall\b",
    ),
    "weight_loss": (
        r"\bweight\s+loss\b",
        r"\blost\s+\d+\s*(kg|pounds?|lbs?)\b",
        r"\bunintentional\s+weight\b",
        r"\bappetite\s+(loss|poor)\b",
    ),
    "medication_issues": (
        r"\bpolypharmacy\b",
        r"\bmissed\s+(dose|medication|meds)\b",
        r"\bnon[- ]?adheren",
        r"\bside[- ]?effect",
        r"\bdrug\s+interaction\b",
    ),
    "cognition": (
        r"\bconfused\b",
        r"\bconfusion\b",
        r"\bmemory\b",
        r"\bdementia\b",
        r"\bforget(ting|ful)\b",
        r"\bdisorient",
    ),
    "mobility": (
        r"\bmobility\b",
        r"\bwalk(ing)?\s+(aid|difficulty|limit)",
        r"\bwheeler?\b",
        r"\bunsteady\b",
        r"\bgait\b",
        r"\bbalance\b",
    ),
}

# Structured field that should capture each cue category.
_CUE_TO_FIELD: dict[str, str] = {
    "falls": "falls_history",
    "weight_loss": "weight_change",
    "medication_issues": "medications",
    "cognition": "cognition",
    "mobility": "mobility",
}


def evaluate_critical_findings(
    clinical: ClinicalOutput | None,
    *,
    transcript: str | None = None,
) -> list[CriticalFinding]:
    """Detect cues in narrative/transcript that lack a corresponding structured field."""

    text = combined_text(clinical, transcript)
    if not text.strip():
        return []

    fields = (clinical.fields if clinical else {}) or {}
    findings: list[CriticalFinding] = []
    lower = text.lower()

    for cue_id, patterns in _CRITICAL_CUES.items():
        matched_span: str | None = None
        for pat in patterns:
            m = re.search(pat, lower, flags=re.IGNORECASE)
            if m:
                matched_span = m.group(0)
                break
        if not matched_span:
            continue
        target_field = _CUE_TO_FIELD[cue_id]
        if field_has_value(fields.get(target_field)):
            continue
        findings.append(
            CriticalFinding(
                finding_id=f"missing_structured_{cue_id}",
                severity="warning",
                evidence_span=matched_span,
                message=(
                    f"Text mentions '{matched_span}' but structured field "
                    f"'{target_field}' is empty — possible omitted critical finding."
                ),
            )
        )

    return findings
