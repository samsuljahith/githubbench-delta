"""Evaluation pipeline stage protocol and orchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.config import AppConfig
from githubbench_delta.core.errors import PipelineError
from githubbench_delta.core.models import RunSummary
from githubbench_delta.pipeline.models import ExperimentSpec


class PipelineStageName(StrEnum):
    """Ordered stages in the GitHubBench-Delta evaluation pipeline."""

    TASK = "task"
    AGENT = "agent"
    TRAJECTORY_LOGGER = "trajectory_logger"
    METRIC_ENGINE = "metric_engine"
    AGGREGATOR = "aggregator"
    DASHBOARD = "dashboard"
    HTML_REPORT = "html_report"
    JSON_REPORT = "json_report"
    CSV_REPORT = "csv_report"


class PipelineContext(BaseModel):
    """Mutable bag of state passed between pipeline stages."""

    run_id: str
    config: AppConfig | None = None
    task_ids: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    summary: RunSummary | None = None
    experiment_spec: ExperimentSpec | None = None

    model_config = {"arbitrary_types_allowed": True}


class PipelineStage(ABC):
    """Single stage in the evaluation pipeline."""

    name: PipelineStageName

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> PipelineContext:
        """Execute this stage and return the updated context."""


class PipelineOrchestrator:
    """Runs configured stages in order."""

    def __init__(self, stages: list[PipelineStage] | None = None) -> None:
        self.stages = stages or []

    def add_stage(self, stage: PipelineStage) -> None:
        self.stages.append(stage)

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if not self.stages:
            raise PipelineError("Pipeline has no stages configured")
        current = ctx
        for stage in self.stages:
            current = await stage.run(current)
        return current


class AgentStage(PipelineStage):
    """Delegate agent+eval execution to ExperimentRunner when a spec is present."""

    name = PipelineStageName.AGENT

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        from githubbench_delta.pipeline.experiment import ExperimentRunner

        if ctx.experiment_spec is None:
            raise PipelineError("AgentStage requires experiment_spec on PipelineContext")
        runner = ExperimentRunner(app_config=ctx.config)
        manifest = await runner.run(ctx.experiment_spec)
        ctx.artifacts["experiment_manifest"] = manifest.model_dump(mode="json")
        ctx.artifacts["experiment_id"] = manifest.experiment_id
        return ctx


class MetricEngineStage(PipelineStage):
    """Thin adapter: evaluation is performed inside PipelineRunner / ExperimentRunner."""

    name = PipelineStageName.METRIC_ENGINE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        # Evaluation already runs during AgentStage / ExperimentRunner.
        ctx.artifacts.setdefault("metric_engine", "delegated_to_pipeline_runner")
        return ctx


class AggregatorStage(PipelineStage):
    """Thin adapter: aggregation is performed by EvaluationEngine."""

    name = PipelineStageName.AGGREGATOR

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.artifacts.setdefault("aggregator", "delegated_to_evaluation_engine")
        return ctx


def default_pipeline_stages() -> list[PipelineStage]:
    """Default Phase 5 stages (no dashboard/reports)."""

    return [AgentStage(), MetricEngineStage(), AggregatorStage()]
