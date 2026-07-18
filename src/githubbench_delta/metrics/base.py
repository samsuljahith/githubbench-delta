"""GitHubBench-Delta evaluation methodology — pluggable metric interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from githubbench_delta.core.config import EvaluatorConfig
from githubbench_delta.core.models import (
    AgentResult,
    DiffStats,
    EvaluationResult,
    ExpectedToolCall,
    FailureExample,
    GoldAnswer,
    MetricGroup,
    MetricResult,
    RepositoryRef,
    SandboxEvent,
    TaskOutput,
    ToolCall,
    Trajectory,
    TrajectoryStep,
    TrialKey,
)
from githubbench_delta.metrics.scoring import tool_calls_from_trajectory


class TaskSnapshot(BaseModel):
    """Serializable task view for evaluators (no dataset/runtime coupling)."""

    id: str
    category: str | None = None
    title: str = ""
    description: str = ""
    prompt: str = ""
    files: list[str] = Field(default_factory=list)
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    difficulty: str | None = None


class TokenUsage(BaseModel):
    """Token counters exposed on MetricContext."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class MetricContext(BaseModel):
    """Inputs available to a methodology evaluator.

    Evaluators must operate only on this context — never on live agents,
    providers, or dataset loaders.
    """

    trial: TrialKey
    task_id: str
    task: TaskSnapshot | None = None
    gold_answer: GoldAnswer | None = None
    alternate_gold_answers: list[GoldAnswer] = Field(default_factory=list)
    expected_output: TaskOutput | None = None
    expected_tool_calls: list[ExpectedToolCall] = Field(default_factory=list)
    failure_examples: list[FailureExample] = Field(default_factory=list)
    agent_result: AgentResult
    trajectory: Trajectory | None = None
    diff_stats: DiffStats | None = None
    diff: DiffStats | None = None
    sandbox_events: list[SandboxEvent] = Field(default_factory=list)
    execution_events: list[SandboxEvent | TrajectoryStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    repository: RepositoryRef | None = None
    prompt: str = ""
    response: str = ""
    latency_ms: float = 0.0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    retries: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)
    experiment_id: str | None = None
    run_metadata: dict[str, Any] = Field(default_factory=dict)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    repository_metadata: dict[str, Any] = Field(default_factory=dict)
    peer_results: list[AgentResult] = Field(default_factory=list)
    peer_evaluations: list[EvaluationResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalize(self) -> MetricContext:
        if self.diff is None and self.diff_stats is not None:
            self.diff = self.diff_stats
        elif self.diff_stats is None and self.diff is not None:
            self.diff_stats = self.diff

        if self.trajectory is None and self.agent_result.trajectory is not None:
            self.trajectory = self.agent_result.trajectory
        if self.diff_stats is None and self.agent_result.diff_stats is not None:
            self.diff_stats = self.agent_result.diff_stats
            self.diff = self.diff_stats
        if not self.sandbox_events and self.agent_result.sandbox_events:
            self.sandbox_events = list(self.agent_result.sandbox_events)

        if not self.tool_calls:
            self.tool_calls = tool_calls_from_trajectory(self.trajectory)

        if not self.execution_events:
            events: list[SandboxEvent | TrajectoryStep] = []
            if self.trajectory is not None:
                events.extend(self.trajectory.steps)
            events.extend(self.sandbox_events)
            self.execution_events = events

        if not self.response and self.agent_result.output.content:
            self.response = self.agent_result.output.content
        if not self.prompt and self.task is not None:
            self.prompt = self.task.prompt

        metrics = self.agent_result.metrics
        if self.latency_ms == 0.0 and metrics.latency_ms:
            self.latency_ms = metrics.latency_ms
        if self.cost_usd == 0.0 and metrics.estimated_cost_usd:
            self.cost_usd = metrics.estimated_cost_usd
        if self.token_usage.total_tokens == 0 and metrics.total_tokens:
            self.token_usage = TokenUsage(
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
            )
        if not self.errors and self.agent_result.error:
            self.errors = [self.agent_result.error]

        if self.retries == 0:
            self.retries = int(self.agent_result.metadata.get("retries", 0) or 0)
        if not self.warnings:
            raw = self.agent_result.metadata.get("warnings")
            if isinstance(raw, list):
                self.warnings = [str(w) for w in raw]
        if not self.trace_ids:
            tid = self.agent_result.metadata.get("trace_id") or self.run_metadata.get("trace_id")
            if tid:
                self.trace_ids = [str(tid)]
        if self.experiment_id is None:
            self.experiment_id = self.run_metadata.get("experiment_id")
        return self

    @classmethod
    def from_agent_result(
        cls,
        *,
        agent_result: AgentResult,
        trial: TrialKey | None = None,
        gold_answer: GoldAnswer | None = None,
        alternate_gold_answers: list[GoldAnswer] | None = None,
        expected_output: TaskOutput | None = None,
        expected_tool_calls: list[ExpectedToolCall] | None = None,
        failure_examples: list[FailureExample] | None = None,
        task: TaskSnapshot | None = None,
        repository: RepositoryRef | None = None,
        prompt: str = "",
        peer_results: list[AgentResult] | None = None,
        peer_evaluations: list[EvaluationResult] | None = None,
        run_metadata: dict[str, Any] | None = None,
        provider_metadata: dict[str, Any] | None = None,
        repository_metadata: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MetricContext:
        """Assemble a MetricContext from an AgentResult and optional gold/task data."""

        key = trial or TrialKey(
            task_id=agent_result.task_id,
            agent_id=agent_result.agent_id,
            trial_index=agent_result.trial_index,
        )
        return cls(
            trial=key,
            task_id=agent_result.task_id,
            task=task,
            gold_answer=gold_answer,
            alternate_gold_answers=alternate_gold_answers or [],
            expected_output=expected_output,
            expected_tool_calls=expected_tool_calls or [],
            failure_examples=failure_examples or [],
            agent_result=agent_result,
            trajectory=agent_result.trajectory,
            diff_stats=agent_result.diff_stats,
            sandbox_events=list(agent_result.sandbox_events),
            repository=repository,
            prompt=prompt or (task.prompt if task else ""),
            response=agent_result.output.content,
            peer_results=peer_results or [],
            peer_evaluations=peer_evaluations or [],
            run_metadata=run_metadata or {},
            provider_metadata=provider_metadata or {},
            repository_metadata=repository_metadata or {},
            metadata=metadata or {},
        )


class BaseMetric(ABC):
    """Pluggable production evaluator. One class per methodology metric."""

    id: str
    display_name: str
    group: MetricGroup
    requires_peer_runs: bool = False

    def __init__(self, config: EvaluatorConfig) -> None:
        if config.id != self.id:
            raise ValueError(f"Config id {config.id!r} does not match metric id {self.id!r}")
        self.config = config
        self.display_name = config.display_name
        self.group = config.group
        self.requires_peer_runs = config.requires_peer_runs or self.requires_peer_runs

    @abstractmethod
    def evaluate(self, ctx: MetricContext) -> MetricResult:
        """Run the full evaluation and return a structured MetricResult."""

    def score(self, ctx: MetricContext) -> float:
        """Return the numeric normalized score for ``ctx``."""

        return self.evaluate(ctx).score

    def details(self, ctx: MetricContext) -> dict[str, Any]:
        """Return diagnostic details for ``ctx``."""

        return self.evaluate(ctx).details

    def reasoning(self, ctx: MetricContext) -> str:
        """Return human-readable reasoning for the assigned score."""

        return self.evaluate(ctx).reasoning

    def metadata(self) -> dict[str, Any]:
        """Return static evaluator metadata (id, group, version, config)."""

        return {
            "id": self.id,
            "display_name": self.display_name,
            "group": self.group.value,
            "version": self.config.version,
            "weight": self.config.weight,
            "enabled": self.config.enabled,
            "strict": self.config.strict,
            "normalization": self.config.normalization.value,
            "confidence_mode": self.config.confidence_mode.value,
            "thresholds": dict(self.config.thresholds),
            "requires_peer_runs": self.requires_peer_runs,
        }

    def _threshold(self, key: str, default: Any = None) -> Any:
        return self.config.thresholds.get(key, default)
