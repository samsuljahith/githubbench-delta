"""Clinical Completeness — required RGA fields present vs missing."""

from __future__ import annotations

from githubbench_delta.healthcare_evaluation.models import (
    REQUIRED_RGA_FIELDS,
    ClinicalOutput,
    CompletenessResult,
    field_has_value,
)


def evaluate_completeness(
    clinical: ClinicalOutput | None,
    *,
    transcript: str | None = None,
) -> CompletenessResult | None:
    """Return completeness when any evidence exists; else None (caller → insufficient_data)."""

    has_fields = bool(clinical and any(field_has_value(v) for v in (clinical.fields or {}).values()))
    has_narrative = bool(clinical and clinical.narrative and clinical.narrative.strip())
    has_transcript = bool(transcript and transcript.strip())
    if not (has_fields or has_narrative or has_transcript):
        return None

    fields = (clinical.fields if clinical else {}) or {}
    present: list[str] = []
    missing: list[str] = []
    for key in REQUIRED_RGA_FIELDS:
        if field_has_value(fields.get(key)):
            present.append(key)
        else:
            missing.append(key)

    total = len(REQUIRED_RGA_FIELDS)
    ratio = round(len(present) / total, 4) if total else None
    detail = None
    if not has_fields and (has_narrative or has_transcript):
        detail = (
            "Narrative/transcript present but structured RGA fields incomplete; "
            f"{len(missing)} of {total} required fields missing."
        )
    elif missing:
        detail = f"{len(missing)} of {total} required RGA fields missing."
    else:
        detail = "All required RGA fields present."

    return CompletenessResult(
        present_fields=present,
        missing_fields=missing,
        completeness_ratio=ratio,
        detail=detail,
    )
