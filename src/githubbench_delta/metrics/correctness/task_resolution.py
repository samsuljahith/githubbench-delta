"""Task Resolution evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import GoldAnswer, MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    criteria_hit_rate,
    evidence_confidence,
    skip_result,
    substring_coverage,
    token_jaccard,
)


class TaskResolutionMetric(BaseMetric):
    """Graded success against gold acceptance criteria for the GitHub task."""

    id: str = "task_resolution"
    display_name: str = "Task Resolution"
    group: MetricGroup = MetricGroup.CORRECTNESS

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        golds = self._golds(ctx)
        if not golds:
            return skip_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                reason="No gold answer provided",
                weight=self.config.weight,
                metric_version=self.config.version,
                strict_zero=self.config.strict,
            )

        response = ctx.response or ctx.agent_result.output.content
        best = 0.0
        best_detail: dict = {}
        for idx, gold in enumerate(golds):
            criteria = gold.acceptance_criteria or []
            hit = criteria_hit_rate(criteria, response) if criteria else 0.0
            overlap = max(
                token_jaccard(gold.content, response),
                substring_coverage(gold.content, response),
            )
            if criteria:
                score = 0.6 * hit + 0.4 * overlap
            else:
                score = overlap
            if score > best:
                best = score
                best_detail = {
                    "gold_index": idx,
                    "criteria_hit_rate": hit,
                    "content_overlap": overlap,
                    "criteria_count": len(criteria),
                }

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=1 if response.strip() else 0,
            expected_items=1,
        )
        improvements = []
        if best < 1.0:
            improvements.append(
                "Cover more acceptance criteria and align response with gold content"
            )
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=best,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"Best match across {len(golds)} gold answer(s): "
                f"criteria_hit={best_detail.get('criteria_hit_rate', 0):.2f}, "
                f"overlap={best_detail.get('content_overlap', 0):.2f}"
            ),
            evidence=[best_detail],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details=best_detail,
        )

    @staticmethod
    def _golds(ctx: MetricContext) -> list[GoldAnswer]:
        out: list[GoldAnswer] = []
        if ctx.gold_answer is not None:
            out.append(ctx.gold_answer)
        out.extend(ctx.alternate_gold_answers)
        return out
