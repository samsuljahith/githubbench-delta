"""Aggregate methodology MetricResults into overall / group scores."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.models import EvaluationResult, MetricGroup, MetricResult, TrialKey
from githubbench_delta.metrics.scoring import clamp01


class AggregationStrategy(StrEnum):
    """Supported aggregation strategies."""

    WEIGHTED_AVERAGE = "weighted_average"


class WeightedScore(BaseModel):
    """Per-metric weighted contribution to an aggregate."""

    metric_id: str
    score: float
    weight: float
    contribution: float
    group: MetricGroup
    skipped: bool = False


class AggregationOutcome(BaseModel):
    """Result of aggregating a set of MetricResults."""

    overall_score: float
    group_scores: dict[str, float] = Field(default_factory=dict)
    confidence_score: float = 0.0
    weighted_scores: list[WeightedScore] = Field(default_factory=list)
    category_score: float | None = None
    strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVERAGE
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricAggregator:
    """Combine MetricResults using configurable strategies."""

    def __init__(
        self,
        strategy: AggregationStrategy | str = AggregationStrategy.WEIGHTED_AVERAGE,
    ) -> None:
        self.strategy = AggregationStrategy(strategy)

    def aggregate(
        self,
        results: list[MetricResult],
        *,
        category: str | None = None,
    ) -> AggregationOutcome:
        """Compute overall, group, and confidence scores.

        Skipped metrics are excluded from weighted averages. Disabled metrics
        should already be omitted by the EvaluationEngine.
        """

        if self.strategy != AggregationStrategy.WEIGHTED_AVERAGE:
            # Future custom strategies plug in here.
            raise NotImplementedError(f"Unsupported strategy: {self.strategy}")

        active = [r for r in results if not r.skipped]
        weighted: list[WeightedScore] = []
        for r in results:
            contrib = 0.0 if r.skipped else r.score * r.weight
            weighted.append(
                WeightedScore(
                    metric_id=r.metric_id,
                    score=r.score,
                    weight=r.weight,
                    contribution=contrib,
                    group=r.group,
                    skipped=r.skipped,
                )
            )

        overall = self._weighted_mean(active)
        group_scores: dict[str, float] = {}
        for group in MetricGroup:
            members = [r for r in active if r.group == group]
            if members:
                group_scores[group.value] = self._weighted_mean(members)

        confidences = [r.confidence for r in active]
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return AggregationOutcome(
            overall_score=clamp01(overall),
            group_scores=group_scores,
            confidence_score=clamp01(confidence),
            weighted_scores=weighted,
            category_score=clamp01(overall) if category else None,
            strategy=self.strategy,
            metadata={"category": category, "active_count": len(active)},
        )

    def to_evaluation_result(
        self,
        trial: TrialKey,
        results: list[MetricResult],
        *,
        category: str | None = None,
    ) -> EvaluationResult:
        """Aggregate and wrap into EvaluationResult."""

        outcome = self.aggregate(results, category=category)
        return EvaluationResult(
            trial=trial,
            metric_results={r.metric_id: r for r in results},
            overall_score=outcome.overall_score,
            group_scores=outcome.group_scores,
            confidence_score=outcome.confidence_score,
            metadata={
                "strategy": outcome.strategy.value,
                "weighted_scores": [w.model_dump(mode="json") for w in outcome.weighted_scores],
                "category": category,
                "category_score": outcome.category_score,
            },
        )

    @staticmethod
    def _weighted_mean(results: list[MetricResult]) -> float:
        if not results:
            return 0.0
        total_w = sum(r.weight for r in results)
        if total_w <= 0:
            return 0.0
        return sum(r.score * r.weight for r in results) / total_w
