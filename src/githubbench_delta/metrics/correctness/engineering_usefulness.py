"""Engineering Usefulness evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    criteria_hit_rate,
    evidence_confidence,
)


class EngineeringUsefulnessMetric(BaseMetric):
    """Deterministic proxy for reviewer-style usefulness of the change."""

    id: str = "engineering_usefulness"
    display_name: str = "Engineering Usefulness"
    group: MetricGroup = MetricGroup.CORRECTNESS

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        response = (ctx.response or "").strip()
        success = ctx.agent_result.success
        criteria = (ctx.gold_answer.acceptance_criteria if ctx.gold_answer else []) or []
        hit = (
            criteria_hit_rate(criteria, response)
            if criteria
            else (1.0 if len(response) >= 40 else 0.4 if response else 0.0)
        )

        score = 0.0
        evidence: list[dict] = []
        if success:
            score += 0.35
            evidence.append({"factor": "success", "value": 0.35})
        if response:
            score += 0.25
            evidence.append({"factor": "non_empty_response", "value": 0.25})
        score += 0.30 * hit
        evidence.append({"factor": "criteria_or_substance", "value": 0.30 * hit})

        vacuous = response.lower() in {"ok", "done", "fixed", "n/a", "none"} or (
            len(response) < 12 and response
        )
        if vacuous:
            score -= 0.25
            evidence.append({"factor": "vacuous_penalty", "value": -0.25})

        err_pen = min(0.2, 0.05 * len(ctx.errors) + 0.02 * len(ctx.warnings))
        if err_pen:
            score -= err_pen
            evidence.append({"factor": "error_warning_penalty", "value": -err_pen})

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(evidence),
            expected_items=4,
        )
        improvements = []
        if not success:
            improvements.append("Produce a successful, complete solution")
        if vacuous:
            improvements.append("Provide a substantive engineering explanation or patch")
        if hit < 1.0 and criteria:
            improvements.append("Address remaining acceptance criteria")

        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=score,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"Usefulness from success={success}, response_len={len(response)}, "
                f"criteria_hit={hit:.2f}, penalties={err_pen + (0.25 if vacuous else 0):.2f}"
            ),
            evidence=evidence,
            warnings=list(ctx.warnings),
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"success": success, "criteria_hit_rate": hit, "vacuous": vacuous},
        )
