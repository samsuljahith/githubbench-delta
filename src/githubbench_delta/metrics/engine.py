"""Evaluation engine — run all methodology metrics on a MetricContext."""

from __future__ import annotations

from githubbench_delta.core.config import AppConfig, load_config
from githubbench_delta.core.models import EvaluationResult
from githubbench_delta.metrics.aggregator import AggregationStrategy, MetricAggregator
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.registry import MetricRegistry


class EvaluationEngine:
    """Run enabled methodology evaluators and aggregate scores.

    Agent-agnostic: operates only on ``MetricContext``. No I/O, cloning,
    or provider calls.
    """

    def __init__(
        self,
        registry: MetricRegistry | None = None,
        *,
        aggregator: MetricAggregator | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        if registry is not None:
            self.registry = registry
        elif app_config is not None:
            self.registry = MetricRegistry.from_app_config(app_config)
        else:
            self.registry = MetricRegistry.from_app_config(load_config())
        self.aggregator = aggregator or MetricAggregator(AggregationStrategy.WEIGHTED_AVERAGE)

    def evaluate(self, ctx: MetricContext) -> EvaluationResult:
        """Evaluate ``ctx`` with all enabled metrics and aggregate."""

        results = []
        for metric in self.registry.enabled_metrics():
            results.append(metric.evaluate(ctx))
        category = ctx.task.category if ctx.task else None
        return self.aggregator.to_evaluation_result(ctx.trial, results, category=category)

    def evaluate_metric(self, metric_id: str, ctx: MetricContext) -> BaseMetric:
        """Return a single metric instance (for isolated testing)."""

        return self.registry.get(metric_id)
