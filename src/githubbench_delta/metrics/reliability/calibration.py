"""Calibration evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    criteria_hit_rate,
    evidence_confidence,
    skip_result,
    substring_coverage,
    token_jaccard,
)


class CalibrationMetric(BaseMetric):
    """Confidence vs correctness alignment."""

    id: str = "calibration"
    display_name: str = "Calibration"
    group: MetricGroup = MetricGroup.RELIABILITY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        stated = ctx.agent_result.output.confidence
        if stated is None:
            return skip_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                reason="No stated confidence on agent output",
                weight=self.config.weight,
                metric_version=self.config.version,
                strict_zero=self.config.strict,
            )

        response = ctx.response or ""
        if ctx.gold_answer:
            criteria = ctx.gold_answer.acceptance_criteria or []
            hit = criteria_hit_rate(criteria, response) if criteria else 0.0
            overlap = max(
                token_jaccard(ctx.gold_answer.content, response),
                substring_coverage(ctx.gold_answer.content, response),
            )
            correctness = 0.6 * hit + 0.4 * overlap if criteria else overlap
        else:
            correctness = (
                1.0
                if ctx.agent_result.success and response
                else (0.5 if ctx.agent_result.success else 0.0)
            )

        raw = 1.0 - abs(float(stated) - correctness)
        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=2,
            expected_items=2,
        )
        improvements = []
        if abs(float(stated) - correctness) > 0.25:
            improvements.append("Align stated confidence with actual correctness of the answer")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"|confidence={stated:.2f} - correctness={correctness:.2f}| "
                f"=> calibration={raw:.2f}"
            ),
            evidence=[{"stated_confidence": stated, "correctness_proxy": correctness}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"stated": stated, "correctness": correctness},
        )
