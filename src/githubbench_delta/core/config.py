"""Configuration loading: YAML files + environment overrides."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from githubbench_delta.core.errors import ConfigurationError
from githubbench_delta.core.models import AgentId, MetricGroup


class NormalizationStrategy(StrEnum):
    """How raw metric scores are normalized to [0, 1]."""

    CLAMP_01 = "clamp_01"
    IDENTITY = "identity"


class ConfidenceMode(StrEnum):
    """How evaluator confidence is derived."""

    EVIDENCE_COVERAGE = "evidence_coverage"
    FIXED = "fixed"


# Stable ids for the 18 GitHubBench-Delta methodology evaluators.
METHODOLOGY_METRIC_IDS: tuple[str, ...] = (
    "task_resolution",
    "engineering_usefulness",
    "diff_minimality",
    "tool_economy",
    "unnecessary_tool_calls",
    "planning_quality",
    "branch_safety",
    "blast_radius",
    "safe_failure",
    "grounding_ratio",
    "hallucinated_api",
    "test_honesty",
    "recovery_score",
    "calibration",
    "cross_trial_consistency",
    "reproducibility",
    "cost_normalized_capability",
    "local_vs_hosted_parity",
)

PEER_RUN_METRIC_IDS: frozenset[str] = frozenset(
    {
        "cross_trial_consistency",
        "reproducibility",
        "local_vs_hosted_parity",
    }
)


class PathsConfig(BaseModel):
    """Filesystem locations for datasets and runtime artifacts."""

    datasets: Path = Path("datasets")
    logs: Path = Path("logs")
    results: Path = Path("results")
    reports: Path = Path("reports")


class StorageConfig(BaseModel):
    """Dual-store paths: SQLite (OLTP) and DuckDB (OLAP)."""

    sqlite_path: Path = Path("results/githubbench.db")
    duckdb_path: Path = Path("results/githubbench.duckdb")


class SandboxConfig(BaseModel):
    """Sandbox / git safety policy used by safety evaluators."""

    protected_branches: list[str] = Field(default_factory=lambda: ["main", "master"])
    allow_network: bool = False
    allow_push: bool = False


class RetryConfig(BaseModel):
    """Retry defaults from configs/default.yaml."""

    max_attempts: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


class EventStoreConfig(BaseModel):
    """Event persistence backend selection."""

    backend: str = "jsonl"  # jsonl | sqlite
    jsonl_path: Path = Path("logs/events.jsonl")
    sqlite_path: Path = Path("results/events.db")


class ObservabilityConfig(BaseModel):
    """Observability toggles."""

    structured_logging: bool = True


class PipelineConfig(BaseModel):
    """Phase 5 evaluation pipeline knobs."""

    max_concurrency: int = 1
    resume: bool = True
    cache_evaluations: bool = True
    results_dir: Path = Path("results/experiments")


class AgentProviderConfig(BaseModel):
    """Connection and generation settings for a single agent provider."""

    id: AgentId
    display_name: str
    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    rate_limit_rpm: int = 60
    enabled: bool = True
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


class EvaluatorConfig(BaseModel):
    """Per-evaluator configuration for the GitHubBench-Delta methodology."""

    id: str
    display_name: str
    group: MetricGroup
    enabled: bool = True
    weight: float = Field(default=1.0, ge=0.0)
    requires_peer_runs: bool = False
    thresholds: dict[str, Any] = Field(default_factory=dict)
    strict: bool = False
    normalization: NormalizationStrategy = NormalizationStrategy.CLAMP_01
    confidence_mode: ConfidenceMode = ConfidenceMode.EVIDENCE_COVERAGE
    version: str = "1.0.0"

    @field_validator("id")
    @classmethod
    def validate_methodology_id(cls, value: str) -> str:
        if value not in METHODOLOGY_METRIC_IDS:
            raise ValueError(
                f"Unknown evaluator id {value!r}; must be one of {METHODOLOGY_METRIC_IDS}"
            )
        return value


# Public alias used by the evaluation engine.
MetricConfiguration = EvaluatorConfig


class DefaultRuntimeConfig(BaseModel):
    """Runtime knobs from configs/default.yaml."""

    seed: int = 42
    trial_count: int = 3
    task_timeout_seconds: int = 600
    max_tool_calls: int = 50
    paths: PathsConfig = Field(default_factory=PathsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    event_store: EventStoreConfig = Field(default_factory=EventStoreConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


class AgentsFileConfig(BaseModel):
    """Root shape of configs/agents.yaml."""

    agents: dict[str, AgentProviderConfig]


class MetricsFileConfig(BaseModel):
    """Root shape of configs/metrics.yaml."""

    evaluators: dict[str, EvaluatorConfig]


class EnvSettings(BaseSettings):
    """Environment-backed secrets and path overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    minicpm_base_url: str | None = None
    minicpm_api_key: str | None = None
    minicpm_model: str | None = None
    github_token: str | None = None
    githubbench_config_dir: Path = Path("configs")
    githubbench_seed: int | None = None


class AppConfig(BaseModel):
    """Aggregated application configuration (single source of truth)."""

    runtime: DefaultRuntimeConfig
    agents: dict[str, AgentProviderConfig]
    evaluators: dict[str, EvaluatorConfig]
    env: EnvSettings

    def get_agent(self, agent_id: AgentId | str) -> AgentProviderConfig:
        key = str(agent_id)
        if key not in self.agents:
            raise ConfigurationError(f"Unknown agent id: {key}")
        return self.agents[key]

    def get_evaluator(self, metric_id: str) -> EvaluatorConfig:
        if metric_id not in self.evaluators:
            raise ConfigurationError(f"Unknown evaluator id: {metric_id}")
        return self.evaluators[metric_id]

    def enabled_evaluators(self) -> list[EvaluatorConfig]:
        return [e for e in self.evaluators.values() if e.enabled]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"Config file must be a mapping: {path}")
    return data


def _apply_env_overrides(runtime: DefaultRuntimeConfig, env: EnvSettings) -> DefaultRuntimeConfig:
    if env.githubbench_seed is not None:
        runtime = runtime.model_copy(update={"seed": env.githubbench_seed})
    return runtime


def _apply_agent_env_overrides(
    agents: dict[str, AgentProviderConfig],
    env: EnvSettings,
) -> dict[str, AgentProviderConfig]:
    updated = dict(agents)
    if AgentId.MINICPM.value in updated:
        minicpm = updated[AgentId.MINICPM.value]
        patches: dict[str, Any] = {}
        if env.minicpm_base_url:
            patches["base_url"] = env.minicpm_base_url
        if env.minicpm_model:
            patches["model"] = env.minicpm_model
        if patches:
            updated[AgentId.MINICPM.value] = minicpm.model_copy(update=patches)
    return updated


def _validate_evaluators(evaluators: dict[str, EvaluatorConfig]) -> None:
    ids = set(evaluators.keys())
    expected = set(METHODOLOGY_METRIC_IDS)
    if ids != expected:
        missing = sorted(expected - ids)
        extra = sorted(ids - expected)
        parts: list[str] = []
        if missing:
            parts.append(f"missing={missing}")
        if extra:
            parts.append(f"extra={extra}")
        raise ConfigurationError(
            "metrics.yaml must define exactly the 18 methodology evaluators; " + ", ".join(parts)
        )
    for metric_id, cfg in evaluators.items():
        if cfg.id != metric_id:
            raise ConfigurationError(
                f"Evaluator key {metric_id!r} does not match id field {cfg.id!r}"
            )
        peer_default = metric_id in PEER_RUN_METRIC_IDS
        if peer_default and not cfg.requires_peer_runs:
            # Keep config authoritative but enforce methodology default for peer metrics.
            cfg.requires_peer_runs = True


def load_config(config_dir: Path | str | None = None) -> AppConfig:
    """Load and validate YAML configs merged with environment settings."""

    env = EnvSettings()
    root = Path(config_dir) if config_dir is not None else env.githubbench_config_dir
    if not root.is_absolute():
        # Resolve relative to process CWD (typically repo root).
        root = root.resolve()

    runtime = DefaultRuntimeConfig.model_validate(_read_yaml(root / "default.yaml"))
    runtime = _apply_env_overrides(runtime, env)

    agents_file = AgentsFileConfig.model_validate(_read_yaml(root / "agents.yaml"))
    agents = _apply_agent_env_overrides(agents_file.agents, env)

    metrics_file = MetricsFileConfig.model_validate(_read_yaml(root / "metrics.yaml"))
    _validate_evaluators(metrics_file.evaluators)

    return AppConfig(
        runtime=runtime,
        agents=agents,
        evaluators=metrics_file.evaluators,
        env=env,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cached config loader for CLI/API convenience."""

    return load_config()


def clear_config_cache() -> None:
    """Clear the cached AppConfig (useful in tests)."""

    get_config.cache_clear()
