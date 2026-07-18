"""Evaluation pipeline orchestration.

Heavy modules (ExperimentRunner, PipelineRunner) are imported lazily to avoid
circular imports with agents ↔ storage ↔ pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from githubbench_delta.pipeline.base import (
    AgentStage,
    AggregatorStage,
    MetricEngineStage,
    PipelineContext,
    PipelineOrchestrator,
    PipelineStage,
    PipelineStageName,
    default_pipeline_stages,
)
from githubbench_delta.pipeline.models import (
    ExperimentManifest,
    ExperimentSpec,
    ExperimentStatus,
    ProgressEvent,
    RunManifest,
    RunStatus,
    WorkUnit,
)

if TYPE_CHECKING:
    from githubbench_delta.pipeline.context_factory import MetricContextFactory
    from githubbench_delta.pipeline.experiment import ExperimentRunner
    from githubbench_delta.pipeline.experiment_manager import ExperimentManager
    from githubbench_delta.pipeline.run_manager import RunManager
    from githubbench_delta.pipeline.runner import PipelineRunner

__all__ = [
    "AgentStage",
    "AggregatorStage",
    "ExperimentManager",
    "ExperimentManifest",
    "ExperimentRunner",
    "ExperimentSpec",
    "ExperimentStatus",
    "MetricContextFactory",
    "MetricEngineStage",
    "PipelineContext",
    "PipelineOrchestrator",
    "PipelineRunner",
    "PipelineStage",
    "PipelineStageName",
    "ProgressEvent",
    "RunManager",
    "RunManifest",
    "RunStatus",
    "WorkUnit",
    "default_pipeline_stages",
]


def __getattr__(name: str) -> Any:
    if name == "ExperimentRunner":
        from githubbench_delta.pipeline.experiment import ExperimentRunner

        return ExperimentRunner
    if name == "ExperimentManager":
        from githubbench_delta.pipeline.experiment_manager import ExperimentManager

        return ExperimentManager
    if name == "RunManager":
        from githubbench_delta.pipeline.run_manager import RunManager

        return RunManager
    if name == "PipelineRunner":
        from githubbench_delta.pipeline.runner import PipelineRunner

        return PipelineRunner
    if name == "MetricContextFactory":
        from githubbench_delta.pipeline.context_factory import MetricContextFactory

        return MetricContextFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
