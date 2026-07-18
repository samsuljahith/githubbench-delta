"""Unnecessary Tool Calls evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    tool_name_sequence,
)


class UnnecessaryToolCallsMetric(BaseMetric):
    """Fraction of non-advancing or unexpected tool calls."""

    id: str = "unnecessary_tool_calls"
    display_name: str = "Unnecessary Tool Calls"
    group: MetricGroup = MetricGroup.TRAJECTORY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        actual = tool_name_sequence(ctx.trajectory) or [c.name for c in ctx.tool_calls]
        expected_set = {c.name for c in ctx.expected_tool_calls}
        max_ratio = float(self._threshold("max_unnecessary_ratio", 0.35))

        unnecessary: list[str] = []
        seen: set[tuple[str, str]] = set()
        for call in ctx.tool_calls or []:
            key = (call.name, str(sorted(call.arguments.items())))
            outside = bool(expected_set) and call.name not in expected_set
            dup = key in seen
            seen.add(key)
            if outside or dup:
                unnecessary.append(call.name)
        # Fallback when only names available
        if not ctx.tool_calls and actual:
            seen_names: set[str] = set()
            for name in actual:
                outside = bool(expected_set) and name not in expected_set
                dup = name in seen_names
                seen_names.add(name)
                if outside or dup:
                    unnecessary.append(name)

        total = max(1, len(actual))
        ratio = len(unnecessary) / total
        # Map ratio to score: at/above max_ratio → 0 contribution floor via linear map
        raw = 1.0 - min(1.0, ratio / max_ratio) if max_ratio > 0 else 1.0 - ratio

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(actual),
            expected_items=max(1, len(expected_set) or len(actual) or 1),
        )
        improvements = []
        if ratio > 0:
            improvements.append("Remove duplicate or out-of-scope tool calls from the trajectory")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"{len(unnecessary)}/{total} unnecessary calls "
                f"(ratio={ratio:.2f}, threshold={max_ratio:.2f})"
            ),
            evidence=[{"unnecessary": unnecessary, "actual": actual}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"unnecessary_ratio": ratio, "threshold": max_ratio},
        )
