"""Shared domain models used across agents, tasks, metrics, and pipeline.

These types are the contracts Phase 2+ implementations build on.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentId(StrEnum):
    """Stable identifiers for supported coding agents."""

    MINICPM = "minicpm"
    CLAUDE = "claude"
    CODEX = "codex"


class Difficulty(StrEnum):
    """Task difficulty band."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TaskCategory(StrEnum):
    """GitHub engineering task categories supported by the framework."""

    REPOSITORY_SEARCH = "repository_search"
    ARCHITECTURE_EXPLANATION = "architecture_explanation"
    ARCHITECTURE_UNDERSTANDING = "architecture_understanding"
    CODE_EXPLANATION = "code_explanation"
    COMMIT_SUMMARY = "commit_summary"
    BUG_FIX = "bug_fix"
    README_GENERATION = "readme_generation"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    PULL_REQUEST_REVIEW = "pull_request_review"
    REFACTORING = "refactoring"
    CODE_REFACTORING = "code_refactoring"
    PR_GENERATION = "pr_generation"
    UNIT_TEST_GENERATION = "unit_test_generation"
    DEAD_CODE_DETECTION = "dead_code_detection"
    ISSUE_ANALYSIS = "issue_analysis"


class MetricGroup(StrEnum):
    """Top-level groups for the GitHubBench-Delta evaluation methodology."""

    CORRECTNESS = "correctness"
    TRAJECTORY = "trajectory"
    SAFETY = "safety"
    GROUNDING = "grounding"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"


class RepositoryRef(BaseModel):
    """Pinned repository reference for a benchmark task."""

    url: str | None = None
    local_path: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    fingerprint: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TaskInput(BaseModel):
    """Normalized input payload presented to an agent for a task."""

    prompt: str
    repository_url: str | None = None
    repository_ref: str | None = None
    files: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class TaskOutput(BaseModel):
    """Agent-produced or expected structured output for a task."""

    content: str = ""
    patch: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class GoldAnswerFormat(StrEnum):
    """Supported gold-answer payload formats."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    PATCH = "patch"
    CODE = "code"
    STRUCTURED = "structured"


class GoldAnswer(BaseModel):
    """Reference / gold standard answer used by correctness evaluators."""

    content: str = ""
    format: GoldAnswerFormat = GoldAnswerFormat.TEXT
    patch: str | None = None
    structured: dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: list[str] = Field(default_factory=list)
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExpectedToolCall(BaseModel):
    """One expected tool invocation in an ordered trajectory gold path.

    Used by future trajectory metrics (Tool Economy, Planning Quality, etc.).
    Argument matching may be partial; evaluators interpret ``arguments`` as
    constraints rather than requiring exact equality unless noted in metadata.
    """

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    optional: bool = False
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class FailureExampleKind(StrEnum):
    """Categories of known incorrect or unsafe task behaviors."""

    INCORRECT_BEHAVIOR = "incorrect_behavior"
    HALLUCINATION = "hallucination"
    HALLUCINATED_API = "hallucinated_api"
    UNSAFE_EDIT = "unsafe_edit"
    INVALID_OUTPUT = "invalid_output"
    BLAST_RADIUS = "blast_radius"
    UNSAFE_FAILURE = "unsafe_failure"
    OTHER = "other"


class FailureExample(BaseModel):
    """Known incorrect behavior associated with a task.

    Feeds future safety/grounding metrics (Hallucinated API, Blast Radius,
    Safe Failure) without requiring later schema migrations.
    """

    kind: FailureExampleKind = FailureExampleKind.INCORRECT_BEHAVIOR
    description: str
    example: str = ""
    structured: dict[str, Any] = Field(default_factory=dict)
    related_metrics: list[str] = Field(
        default_factory=list,
        description=(
            "Optional methodology metric ids this example informs, e.g. "
            "hallucinated_api, blast_radius, safe_failure, tool_economy."
        ),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskMetadata(BaseModel):
    """Non-scoring metadata attached to a task instance."""

    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    language: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A single tool invocation requested by an agent."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class ToolResult(BaseModel):
    """Result returned from executing a tool call."""

    call_id: str
    name: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrajectoryStep(BaseModel):
    """One step in an agent trajectory (thought, tool, or message)."""

    index: int
    kind: str
    content: str = ""
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trajectory(BaseModel):
    """Full ordered record of an agent run for a single trial."""

    agent_id: AgentId
    task_id: str
    trial_index: int = 0
    steps: list[TrajectoryStep] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiffStats(BaseModel):
    """Git diff statistics used by Diff Minimality and Blast Radius."""

    changed_files: list[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    patch: str | None = None
    justified_files: list[str] = Field(default_factory=list)


class SandboxEvent(BaseModel):
    """Policy / sandbox event (branch writes, network, destructive ops)."""

    kind: str
    severity: str = "info"
    message: str
    allowed: bool = True
    timestamp: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class TrialKey(BaseModel):
    """Identifies a single trial of an agent on a task under a seed."""

    task_id: str
    agent_id: AgentId
    trial_index: int = 0
    seed: int = 42


class AgentMetrics(BaseModel):
    """Runtime efficiency counters collected during an agent run."""

    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_call_count: int = 0
    error_count: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Complete result of an agent executing one task trial."""

    agent_id: AgentId
    task_id: str
    trial_index: int = 0
    success: bool = False
    output: TaskOutput = Field(default_factory=TaskOutput)
    trajectory: Trajectory | None = None
    diff_stats: DiffStats | None = None
    sandbox_events: list[SandboxEvent] = Field(default_factory=list)
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricResult(BaseModel):
    """Score and details produced by a single methodology evaluator."""

    metric_id: str
    display_name: str
    group: MetricGroup
    raw_score: float = 0.0
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    weight: float = 1.0
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = ""
    evidence: list[Any] | dict[str, Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(default_factory=list)
    metric_version: str = "1.0.0"
    details: dict[str, Any] = Field(default_factory=dict)
    skipped: bool = False
    skip_reason: str | None = None


class EvaluationResult(BaseModel):
    """Per-trial evaluation aggregating all methodology metric results."""

    trial: TrialKey
    metric_results: dict[str, MetricResult] = Field(default_factory=dict)
    overall_score: float | None = None
    group_scores: dict[str, float] = Field(default_factory=dict)
    confidence_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    """Summary of a full evaluation run across agents, tasks, and trials."""

    run_id: str
    seed: int
    agent_ids: list[AgentId] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    evaluations: list[EvaluationResult] = Field(default_factory=list)
    overall_scores: dict[str, float] = Field(default_factory=dict)
    group_scores: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
