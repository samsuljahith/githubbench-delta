"""Planning Quality evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    lcs_ratio,
    skip_result,
    tool_name_sequence,
)


class PlanningQualityMetric(BaseMetric):
    """Plan coherence vs executed tool trajectory (LCS against expected)."""

    id: str = "planning_quality"
    display_name: str = "Planning Quality"
    group: MetricGroup = MetricGroup.TRAJECTORY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        expected = [c.name for c in ctx.expected_tool_calls]
        actual = tool_name_sequence(ctx.trajectory) or [c.name for c in ctx.tool_calls]

        if not expected:
            if not actual:
                return skip_result(
                    metric_id=self.id,
                    display_name=self.display_name,
                    group=self.group,
                    reason="No expected or actual tool trajectory",
                    weight=self.config.weight,
                    metric_version=self.config.version,
                    strict_zero=self.config.strict,
                )
            # Weak heuristic: unique ordered tools without thrashing
            unique = list(dict.fromkeys(actual))
            thrash = 1.0 - (len(unique) / len(actual))
            raw = max(0.0, 0.7 - 0.5 * thrash)
            return build_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                raw_score=raw,
                weight=self.config.weight,
                normalization=self.config.normalization,
                confidence=0.4,
                reasoning=(
                    "No expected tools; weak planning score from thrash="
                    f"{thrash:.2f} on {len(actual)} calls"
                ),
                evidence=[{"actual": actual, "unique": unique}],
                suggested_improvements=[
                    "Provide expected_tool_calls for stronger planning evaluation"
                ],
                metric_version=self.config.version,
                details={"mode": "weak_heuristic", "thrash": thrash},
            )

        raw = lcs_ratio(expected, actual)
        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(actual),
            expected_items=len(expected),
        )
        improvements = []
        if raw < 1.0:
            improvements.append("Execute tools in an order closer to the gold plan sequence")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(f"LCS ratio between expected and actual tool sequences: {raw:.2f}"),
            evidence=[{"expected": expected, "actual": actual}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"lcs_ratio": raw},
        )
