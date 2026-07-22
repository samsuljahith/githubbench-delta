"""Human review status helpers."""

from __future__ import annotations

from githubbench_delta.healthcare_evaluation.models import ReviewStatus


def resolve_review_status(
    requested: ReviewStatus | None,
    *,
    default: ReviewStatus = ReviewStatus.PENDING,
) -> ReviewStatus:
    """New reports default to pending; request may override for clinician workflow."""

    if requested is None:
        return default
    return requested


def is_valid_transition(current: ReviewStatus, new: ReviewStatus) -> bool:
    """All transitions allowed for demo workflow (clinician may set any state)."""

    _ = (current, new)
    return True
