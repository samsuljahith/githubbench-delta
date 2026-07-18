"""GitHubBench-Delta evaluation methodology metrics."""

from githubbench_delta.core.config import MetricConfiguration
from githubbench_delta.metrics.aggregator import (
    AggregationOutcome,
    AggregationStrategy,
    MetricAggregator,
    WeightedScore,
)
from githubbench_delta.metrics.base import BaseMetric, MetricContext, TaskSnapshot, TokenUsage
from githubbench_delta.metrics.engine import EvaluationEngine
from githubbench_delta.metrics.registry import (
    MetricRegistry,
    catalog_entries,
    create_metric,
    create_metrics_from_app_config,
    get_metric_class,
    get_metric_group,
    list_metric_ids,
    register_metric,
)

__all__ = [
    "AggregationOutcome",
    "AggregationStrategy",
    "BaseMetric",
    "EvaluationEngine",
    "MetricAggregator",
    "MetricConfiguration",
    "MetricContext",
    "MetricRegistry",
    "TaskSnapshot",
    "TokenUsage",
    "WeightedScore",
    "catalog_entries",
    "create_metric",
    "create_metrics_from_app_config",
    "get_metric_class",
    "get_metric_group",
    "list_metric_ids",
    "register_metric",
]
