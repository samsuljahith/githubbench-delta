"""Registry of the 18 GitHubBench-Delta methodology evaluators."""

from __future__ import annotations

from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS, AppConfig, EvaluatorConfig
from githubbench_delta.core.errors import RegistryError
from githubbench_delta.core.models import MetricGroup
from githubbench_delta.metrics.base import BaseMetric
from githubbench_delta.metrics.correctness.diff_minimality import DiffMinimalityMetric
from githubbench_delta.metrics.correctness.engineering_usefulness import (
    EngineeringUsefulnessMetric,
)
from githubbench_delta.metrics.correctness.task_resolution import TaskResolutionMetric
from githubbench_delta.metrics.efficiency.cost_normalized_capability import (
    CostNormalizedCapabilityMetric,
)
from githubbench_delta.metrics.efficiency.local_vs_hosted_parity import (
    LocalVsHostedParityMetric,
)
from githubbench_delta.metrics.efficiency.reproducibility import ReproducibilityMetric
from githubbench_delta.metrics.grounding.grounding_ratio import GroundingRatioMetric
from githubbench_delta.metrics.grounding.hallucinated_api import HallucinatedAPIMetric
from githubbench_delta.metrics.grounding.test_honesty import TestHonestyMetric
from githubbench_delta.metrics.reliability.calibration import CalibrationMetric
from githubbench_delta.metrics.reliability.cross_trial_consistency import (
    CrossTrialConsistencyMetric,
)
from githubbench_delta.metrics.reliability.recovery_score import RecoveryScoreMetric
from githubbench_delta.metrics.safety.blast_radius import BlastRadiusMetric
from githubbench_delta.metrics.safety.branch_safety import BranchSafetyMetric
from githubbench_delta.metrics.safety.safe_failure import SafeFailureMetric
from githubbench_delta.metrics.trajectory.planning_quality import PlanningQualityMetric
from githubbench_delta.metrics.trajectory.tool_economy import ToolEconomyMetric
from githubbench_delta.metrics.trajectory.unnecessary_tool_calls import (
    UnnecessaryToolCallsMetric,
)

_METRIC_CLASSES: dict[str, type[BaseMetric]] = {
    "task_resolution": TaskResolutionMetric,
    "engineering_usefulness": EngineeringUsefulnessMetric,
    "diff_minimality": DiffMinimalityMetric,
    "tool_economy": ToolEconomyMetric,
    "unnecessary_tool_calls": UnnecessaryToolCallsMetric,
    "planning_quality": PlanningQualityMetric,
    "branch_safety": BranchSafetyMetric,
    "blast_radius": BlastRadiusMetric,
    "safe_failure": SafeFailureMetric,
    "grounding_ratio": GroundingRatioMetric,
    "hallucinated_api": HallucinatedAPIMetric,
    "test_honesty": TestHonestyMetric,
    "recovery_score": RecoveryScoreMetric,
    "calibration": CalibrationMetric,
    "cross_trial_consistency": CrossTrialConsistencyMetric,
    "reproducibility": ReproducibilityMetric,
    "cost_normalized_capability": CostNormalizedCapabilityMetric,
    "local_vs_hosted_parity": LocalVsHostedParityMetric,
}

_GROUP_MEMBERSHIP: dict[str, MetricGroup] = {
    "task_resolution": MetricGroup.CORRECTNESS,
    "engineering_usefulness": MetricGroup.CORRECTNESS,
    "diff_minimality": MetricGroup.CORRECTNESS,
    "tool_economy": MetricGroup.TRAJECTORY,
    "unnecessary_tool_calls": MetricGroup.TRAJECTORY,
    "planning_quality": MetricGroup.TRAJECTORY,
    "branch_safety": MetricGroup.SAFETY,
    "blast_radius": MetricGroup.SAFETY,
    "safe_failure": MetricGroup.SAFETY,
    "grounding_ratio": MetricGroup.GROUNDING,
    "hallucinated_api": MetricGroup.GROUNDING,
    "test_honesty": MetricGroup.GROUNDING,
    "recovery_score": MetricGroup.RELIABILITY,
    "calibration": MetricGroup.RELIABILITY,
    "cross_trial_consistency": MetricGroup.RELIABILITY,
    "reproducibility": MetricGroup.EFFICIENCY,
    "cost_normalized_capability": MetricGroup.EFFICIENCY,
    "local_vs_hosted_parity": MetricGroup.EFFICIENCY,
}


def register_metric(metric_id: str, cls: type[BaseMetric]) -> None:
    """Register or replace a methodology evaluator class."""

    if metric_id not in METHODOLOGY_METRIC_IDS:
        raise RegistryError(f"Cannot register non-methodology metric id {metric_id!r}")
    _METRIC_CLASSES[metric_id] = cls


def list_metric_ids() -> list[str]:
    """Return the 18 methodology metric ids in canonical order."""

    return list(METHODOLOGY_METRIC_IDS)


def get_metric_group(metric_id: str) -> MetricGroup:
    """Return the methodology group for a metric id."""

    try:
        return _GROUP_MEMBERSHIP[metric_id]
    except KeyError as exc:
        raise RegistryError(f"Unknown metric id: {metric_id}") from exc


def get_metric_class(metric_id: str) -> type[BaseMetric]:
    """Lookup the evaluator class for a methodology metric id."""

    try:
        return _METRIC_CLASSES[metric_id]
    except KeyError as exc:
        raise RegistryError(f"No metric class registered for {metric_id}") from exc


def create_metric(config: EvaluatorConfig) -> BaseMetric:
    """Instantiate an evaluator from its configuration."""

    cls = get_metric_class(config.id)
    return cls(config)


def create_metrics_from_app_config(app_config: AppConfig) -> dict[str, BaseMetric]:
    """Create all evaluators defined in application config (enabled or not)."""

    return {mid: create_metric(cfg) for mid, cfg in app_config.evaluators.items()}


def catalog_entries(app_config: AppConfig) -> list[dict[str, object]]:
    """Build catalog rows for CLI/API (id, display_name, group, weight, enabled)."""

    rows: list[dict[str, object]] = []
    for metric_id in METHODOLOGY_METRIC_IDS:
        cfg = app_config.evaluators[metric_id]
        rows.append(
            {
                "id": cfg.id,
                "display_name": cfg.display_name,
                "group": cfg.group.value,
                "weight": cfg.weight,
                "enabled": cfg.enabled,
                "requires_peer_runs": cfg.requires_peer_runs,
            }
        )
    return rows


class MetricRegistry:
    """Auto-populated registry of the 18 methodology evaluators."""

    def __init__(self) -> None:
        self._metrics: dict[str, BaseMetric] = {}

    def register(self, metric: BaseMetric) -> None:
        self._metrics[metric.id] = metric

    def get(self, metric_id: str) -> BaseMetric:
        try:
            return self._metrics[metric_id]
        except KeyError as exc:
            raise RegistryError(f"Unknown metric id: {metric_id}") from exc

    def list_ids(self) -> list[str]:
        return [mid for mid in METHODOLOGY_METRIC_IDS if mid in self._metrics]

    def all(self) -> list[BaseMetric]:
        return [self._metrics[mid] for mid in self.list_ids()]

    def enabled_metrics(self) -> list[BaseMetric]:
        return [m for m in self.all() if m.config.enabled]

    def __len__(self) -> int:
        return len(self._metrics)

    def __contains__(self, metric_id: object) -> bool:
        return isinstance(metric_id, str) and metric_id in self._metrics

    @classmethod
    def from_app_config(cls, app_config: AppConfig) -> MetricRegistry:
        """Instantiate and register all methodology evaluators from config."""

        registry = cls()
        for metric_id in METHODOLOGY_METRIC_IDS:
            cfg = app_config.evaluators[metric_id]
            registry.register(create_metric(cfg))
        return registry

    @classmethod
    def create_default(cls) -> MetricRegistry:
        """Load default YAML configs and build a full registry."""

        from githubbench_delta.core.config import load_config

        return cls.from_app_config(load_config())
