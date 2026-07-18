"""Cost-Normalized Capability evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    criteria_hit_rate,
    evidence_confidence,
    substring_coverage,
    token_jaccard,
)


class CostNormalizedCapabilityMetric(BaseMetric):
    """Quality per unit cost (deterministic capability proxy)."""

    id: str = "cost_normalized_capability"
    display_name: str = "Cost-Normalized Capability"
    group: MetricGroup = MetricGroup.EFFICIENCY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        k = float(self._threshold("cost_scale", 10.0))
        response = ctx.response or ""
        if ctx.gold_answer:
            criteria = ctx.gold_answer.acceptance_criteria or []
            hit = criteria_hit_rate(criteria, response) if criteria else 0.0
            overlap = max(
                token_jaccard(ctx.gold_answer.content, response),
                substring_coverage(ctx.gold_answer.content, response),
            )
            capability = 0.5 * (1.0 if ctx.agent_result.success else 0.0) + 0.5 * (
                0.6 * hit + 0.4 * overlap if criteria else overlap
            )
        else:
            capability = (
                1.0
                if ctx.agent_result.success and response
                else (0.5 if ctx.agent_result.success else 0.0)
            )

        cost = max(0.0, float(ctx.cost_usd))
        # Also consider token spend as soft cost if USD is zero
        if cost == 0.0 and ctx.token_usage.total_tokens:
            cost = ctx.token_usage.total_tokens / 1_000_000.0  # micro-cost proxy

        raw = capability / (1.0 + cost * k)
        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=2,
            expected_items=2,
        )
        improvements = []
        if cost > 0 and capability < 1.0:
            improvements.append("Improve task success while reducing token/USD cost")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(f"capability={capability:.2f} / (1 + cost={cost:.4f} * k={k}) = {raw:.2f}"),
            evidence=[{"capability": capability, "cost_usd": cost, "k": k}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"capability": capability, "cost": cost},
        )
