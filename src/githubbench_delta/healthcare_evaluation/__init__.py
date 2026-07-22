"""Additive Healthcare Evaluation Layer.

Evaluates submitted clinical / RGA-style evidence with rule-based checks.
Completely separate from GitHubBench-Delta's 18 engineering metrics.
"""

from githubbench_delta.healthcare_evaluation.engine import evaluate_healthcare
from githubbench_delta.healthcare_evaluation.models import (
    ClinicalOutput,
    HealthcareEvaluateRequest,
    HealthcareReport,
    ReviewStatus,
)

__all__ = [
    "ClinicalOutput",
    "HealthcareEvaluateRequest",
    "HealthcareReport",
    "ReviewStatus",
    "evaluate_healthcare",
]
