"""Framework exception hierarchy."""

from __future__ import annotations


class GitHubBenchError(Exception):
    """Base exception for all GitHubBench-Delta errors."""


class RecoverableError(GitHubBenchError):
    """Failure that may succeed on retry."""


class FatalError(GitHubBenchError):
    """Non-retryable failure that aborts the current trial."""


class ConfigurationError(GitHubBenchError):
    """Raised when configuration is missing, invalid, or inconsistent."""


class AgentError(GitHubBenchError):
    """Raised when an agent fails to execute a task or tool."""


class TaskError(GitHubBenchError):
    """Raised when a task definition is invalid or cannot be prepared."""


class DatasetValidationError(TaskError):
    """Raised when a dataset record or corpus fails schema/validation checks."""


class MetricError(GitHubBenchError):
    """Raised when a metric evaluator fails or receives an invalid context."""


class PipelineError(GitHubBenchError):
    """Raised when a pipeline stage fails or the orchestrator misconfigures."""


class RegistryError(GitHubBenchError):
    """Raised when a registry lookup or registration fails."""


class ProviderError(RecoverableError):
    """Provider/SDK call failed in a potentially retryable way."""


class RateLimitError(ProviderError):
    """Provider rate limit or quota exceeded."""


class ToolExecutionError(RecoverableError):
    """Tool invocation failed (missing path, API error, validation, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        fatal: bool = False,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.fatal = fatal
