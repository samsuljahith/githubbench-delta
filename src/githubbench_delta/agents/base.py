"""Agent interface with concrete execution lifecycle (Phase 2)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from githubbench_delta.agents.providers.base import (
    ChatMessage,
    ProviderAdapter,
    ProviderResponse,
)
from githubbench_delta.core.config import AgentProviderConfig, RetryConfig
from githubbench_delta.core.errors import FatalError, ProviderError, RecoverableError
from githubbench_delta.core.models import (
    AgentId,
    AgentMetrics,
    AgentResult,
    TaskOutput,
    ToolCall,
    ToolResult,
)
from githubbench_delta.core.retry import RetryPolicy
from githubbench_delta.observability.context import bind_context
from githubbench_delta.observability.ids import new_run_id
from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tools.base import ToolContext
from githubbench_delta.tools.executor import ToolExecutor
from githubbench_delta.tools.registry import ToolRegistry, create_default_github_registry
from githubbench_delta.trajectory.events import LifecycleStage
from githubbench_delta.trajectory.logger import TrajectoryLogger


class BaseAgent:
    """Abstract coding agent with a template-method lifecycle.

    Public Phase 1 contract preserved:
    ``run_task``, ``execute_tool``, ``get_metrics``.

    Lifecycle::

        initialize → prepare_task → plan → execute → validate → cleanup
    """

    agent_id: AgentId
    display_name: str
    system_prompt: str = (
        "You are a careful software engineering agent working on GitHub tasks. "
        "Use read-only tools to inspect the repository before answering. "
        "Prefer concise, grounded answers. Do not invent files or APIs."
    )

    def __init__(
        self,
        config: AgentProviderConfig,
        *,
        provider: ProviderAdapter | None = None,
        tool_registry: ToolRegistry | None = None,
        event_store: EventStore | None = None,
        retry_config: RetryConfig | None = None,
        max_tool_calls: int = 50,
        github_token: str | None = None,
    ) -> None:
        self.config = config
        self.agent_id = config.id
        self.display_name = config.display_name
        self._metrics = AgentMetrics()
        self._provider = provider
        self._tool_registry = tool_registry or create_default_github_registry()
        self._tool_executor = ToolExecutor(self._tool_registry)
        self._event_store = event_store
        self._retry_config = retry_config or RetryConfig()
        self._max_tool_calls = max_tool_calls
        self._github_token = github_token or os.environ.get("GITHUB_TOKEN")

        # Per-run state
        self._logger: TrajectoryLogger | None = None
        self._task: BaseTask | None = None
        self._messages: list[ChatMessage] = []
        self._tool_context: ToolContext | None = None
        self._final_text: str = ""
        self._success: bool = False
        self._error: str | None = None
        self._run_id: str = ""
        self._trial_index: int = 0
        self._obs_cm: Any = None

    @property
    def provider(self) -> ProviderAdapter:
        if self._provider is None:
            raise FatalError(f"{self.__class__.__name__} has no provider adapter")
        return self._provider

    def get_metrics(self) -> AgentMetrics:
        """Return cumulative runtime metrics for the current/last run."""

        return self._metrics.model_copy(deep=True)

    def reset_metrics(self) -> None:
        """Reset cumulative metrics before a new trial."""

        self._metrics = AgentMetrics()

    async def run_task(self, task: BaseTask, *, trial_index: int = 0) -> AgentResult:
        """Execute the full lifecycle and return a structured ``AgentResult``."""

        self._trial_index = trial_index
        self._task = task
        self._final_text = ""
        self._success = False
        self._error = None
        try:
            await self.initialize()
            await self.prepare_task()
            await self.plan()
            await self.execute()
            await self.validate()
        except FatalError as exc:
            self._error = str(exc)
            self._success = False
            self._metrics.error_count += 1
            if self._logger is not None:
                self._logger.emit(
                    LifecycleStage.EXECUTE,
                    error=str(exc),
                    level="error",
                )
        except Exception as exc:  # noqa: BLE001
            self._error = f"{type(exc).__name__}: {exc}"
            self._success = False
            self._metrics.error_count += 1
            if self._logger is not None:
                self._logger.emit(
                    LifecycleStage.EXECUTE,
                    error=self._error,
                    level="error",
                )
        return await self.cleanup()

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call via the tool executor."""

        context = self._tool_context or ToolContext(github_token=self._github_token)
        started = time.perf_counter()
        result = await self._tool_executor.execute(tool_call, context)
        latency_ms = (time.perf_counter() - started) * 1000
        self._metrics.tool_call_count += 1
        if not result.success:
            self._metrics.error_count += 1
        if self._logger is not None:
            self._logger.emit(
                LifecycleStage.TOOL,
                tool=tool_call.name,
                arguments=tool_call.arguments,
                result=result.output if result.success else None,
                latency_ms=result.duration_ms or latency_ms,
                error=result.error,
            )
        return result

    async def initialize(self) -> None:
        """Reset metrics, bind run/trace IDs, open trajectory logger."""

        self.reset_metrics()
        self._run_id = new_run_id()
        task = self._require_task()
        self._obs_cm = bind_context(
            run_id=self._run_id,
            agent_id=str(self.agent_id),
            task_id=task.id,
        )
        self._obs_cm.__enter__()
        self._logger = TrajectoryLogger(
            run_id=self._run_id,
            agent_id=self.agent_id,
            task_id=task.id,
            trial_index=self._trial_index,
            event_store=self._event_store,
        )
        self._logger.emit(LifecycleStage.INITIALIZE, result="ok")

    async def prepare_task(self) -> None:
        """Validate task and build messages + tool context."""

        task = self._require_task()
        task.validate()
        repo_path = None
        raw_path = task.input.context.get("repo_path")
        if isinstance(raw_path, str) and raw_path:
            repo_path = Path(raw_path)
        self._tool_context = ToolContext(
            repo_path=repo_path,
            repository_url=task.input.repository_url,
            repository_ref=task.input.repository_ref,
            github_token=self._github_token,
        )
        self._messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=task.to_prompt()),
        ]
        assert self._logger is not None
        self._logger.emit(
            LifecycleStage.PREPARE_TASK,
            result={"message_count": len(self._messages)},
            metadata={"repo_path": str(repo_path) if repo_path else None},
        )

    async def plan(self) -> None:
        """Emit a planning event describing the intended approach."""

        task = self._require_task()
        plan_text = (
            f"Investigate task '{task.id}' ({task.category.value}) "
            f"using read-only tools, then produce a grounded answer."
        )
        assert self._logger is not None
        self._logger.emit(LifecycleStage.PLAN, result=plan_text, content=plan_text)

    async def execute(self) -> None:
        """Provider tool loop until final text or max tool calls."""

        assert self._logger is not None
        tools = self._tool_registry.specs()
        tool_calls_used = 0
        for _ in range(self._max_tool_calls + 1):
            started = time.perf_counter()
            try:
                response = await self.provider.complete(self._messages, tools)
            except (ProviderError, RecoverableError) as exc:
                self._metrics.error_count += 1
                self._logger.emit(
                    LifecycleStage.PROVIDER,
                    error=str(exc),
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                raise
            latency_ms = (time.perf_counter() - started) * 1000
            self._record_usage(response, latency_ms)
            self._logger.emit(
                LifecycleStage.PROVIDER,
                result=response.text or f"tool_calls={len(response.tool_calls)}",
                latency_ms=latency_ms,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                cost_usd=self._estimate_cost(response),
                content=response.text,
            )

            if response.tool_calls:
                assistant_msg = ChatMessage(
                    role="assistant",
                    content=response.text or None,
                    tool_calls=list(response.raw.get("tool_calls") or []),
                )
                # Ensure raw tool_calls present for provider message history
                if not assistant_msg.tool_calls:
                    assistant_msg.tool_calls = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                self._messages.append(assistant_msg)
                for tc in response.tool_calls:
                    if tool_calls_used >= self._max_tool_calls:
                        raise FatalError("max_tool_calls exceeded")
                    result = await self.execute_tool(tc)
                    tool_calls_used += 1
                    self._messages.append(
                        ChatMessage(
                            role="tool",
                            content=result.output if result.success else (result.error or ""),
                            tool_call_id=tc.id,
                            name=tc.name,
                        )
                    )
                continue

            self._final_text = response.text or ""
            self._messages.append(ChatMessage(role="assistant", content=self._final_text))
            self._logger.emit(
                LifecycleStage.EXECUTE,
                result="completed",
                metadata={"tool_calls_used": tool_calls_used},
            )
            return

        raise FatalError("Agent loop ended without a final response")

    async def validate(self) -> None:
        """Mark success when a non-empty final answer is present."""

        self._success = bool(self._final_text.strip()) and self._error is None
        assert self._logger is not None
        self._logger.emit(
            LifecycleStage.VALIDATE,
            result={"success": self._success},
            warning=None if self._success else "empty_or_failed_output",
        )
        if not self._success and self._error is None:
            self._error = "Agent produced empty output"

    async def cleanup(self) -> AgentResult:
        """Flush logger, clear context, return ``AgentResult``."""

        task = self._require_task()
        trajectory = None
        if self._logger is not None:
            self._logger.emit(LifecycleStage.CLEANUP, result="ok")
            trajectory = self._logger.build_trajectory()
            self._logger.flush()
        if self._obs_cm is not None:
            self._obs_cm.__exit__(None, None, None)
            self._obs_cm = None
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            trial_index=self._trial_index,
            success=self._success,
            output=TaskOutput(content=self._final_text),
            trajectory=trajectory,
            metrics=self.get_metrics(),
            error=self._error,
            metadata={"run_id": self._run_id},
        )

    def _require_task(self) -> BaseTask:
        if self._task is None:
            raise FatalError("No task bound to agent")
        return self._task

    def _record_usage(self, response: ProviderResponse, latency_ms: float) -> None:
        self._metrics.latency_ms += latency_ms
        self._metrics.prompt_tokens += response.usage.prompt_tokens
        self._metrics.completion_tokens += response.usage.completion_tokens
        self._metrics.total_tokens += response.usage.total_tokens or (
            response.usage.prompt_tokens + response.usage.completion_tokens
        )
        self._metrics.estimated_cost_usd += self._estimate_cost(response)

    def _estimate_cost(self, response: ProviderResponse) -> float:
        inp = (response.usage.prompt_tokens / 1000.0) * self.config.input_cost_per_1k
        out = (response.usage.completion_tokens / 1000.0) * self.config.output_cost_per_1k
        return inp + out

    def retry_policy(self) -> RetryPolicy:
        cfg = self._retry_config
        return RetryPolicy(
            max_attempts=cfg.max_attempts,
            base_delay_s=cfg.base_delay_s,
            max_delay_s=cfg.max_delay_s,
            exponential_base=cfg.exponential_base,
            jitter=cfg.jitter,
        )
