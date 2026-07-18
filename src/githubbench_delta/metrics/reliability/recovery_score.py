"""Recovery Score evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import build_result, evidence_confidence


class RecoveryScoreMetric(BaseMetric):
    """Recovery after tool/errors in the trajectory."""

    id: str = "recovery_score"
    display_name: str = "Recovery Score"
    group: MetricGroup = MetricGroup.RELIABILITY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        failures: list[int] = []
        recoveries = 0
        steps = ctx.trajectory.steps if ctx.trajectory else []

        for i, step in enumerate(steps):
            failed = False
            if step.tool_result is not None and not step.tool_result.success:
                failed = True
            if step.kind == "error":
                failed = True
            if failed:
                failures.append(i)
                # Look ahead for a later successful tool call
                for later in steps[i + 1 :]:
                    if later.tool_result is not None and later.tool_result.success:
                        recoveries += 1
                        break
                    if later.kind in {"assistant", "final"} and later.content:
                        recoveries += 1
                        break

        if not failures:
            # No failures — perfect recovery score; also credit explicit retries
            raw = 1.0 if ctx.retries == 0 or ctx.agent_result.success else 0.85
            reasoning = "No tool/error failures observed in trajectory"
        else:
            raw = recoveries / len(failures)
            reasoning = (
                f"Recovered from {recoveries}/{len(failures)} failure event(s); "
                f"retries={ctx.retries}"
            )

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(failures) + 1,
            expected_items=max(1, len(failures) or 1),
        )
        improvements = []
        if failures and raw < 1.0:
            improvements.append(
                "After a tool error, retry with a corrected call or alternate strategy"
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
            evidence=[{"failure_indices": failures, "recoveries": recoveries}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"failure_count": len(failures), "recovery_count": recoveries},
        )
