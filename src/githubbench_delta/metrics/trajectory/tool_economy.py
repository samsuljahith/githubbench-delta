"""Tool Economy evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    multiset_f1,
    tool_name_sequence,
)


class ToolEconomyMetric(BaseMetric):
    """Useful tool calls per unit of resolved work."""

    id: str = "tool_economy"
    display_name: str = "Tool Economy"
    group: MetricGroup = MetricGroup.TRAJECTORY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        actual = tool_name_sequence(ctx.trajectory) or [c.name for c in ctx.tool_calls]
        budget = float(self._threshold("max_tool_calls_budget", 30))
        expected = [c.name for c in ctx.expected_tool_calls]

        if expected:
            raw = multiset_f1(expected, actual)
            reasoning = (
                f"Tool-name F1 vs expected trajectory: {raw:.2f} "
                f"(expected={len(expected)}, actual={len(actual)})"
            )
            improvements = (
                ["Align tool usage with the expected gold trajectory"] if raw < 1.0 else []
            )
        else:
            ratio = min(1.0, len(actual) / budget) if budget > 0 else 0.0
            capability = 1.0 if ctx.agent_result.success else 0.4
            raw = capability * (1.0 - ratio)
            reasoning = (
                f"No expected tools; budget score from {len(actual)}/{budget} calls "
                f"gated by success={ctx.agent_result.success}"
            )
            improvements = (
                ["Reduce unnecessary tool calls within the budget"] if ratio > 0.5 else []
            )

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(actual) + len(expected),
            expected_items=max(1, len(expected) or 1),
        )
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=reasoning,
            evidence=[{"expected": expected, "actual": actual, "budget": budget}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"actual_count": len(actual), "expected_count": len(expected)},
        )
