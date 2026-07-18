"""Agent lifecycle and trajectory event tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.agents.base import BaseAgent
from githubbench_delta.agents.providers.base import (
    ChatMessage,
    ProviderAdapter,
    ProviderResponse,
    ProviderUsage,
)
from githubbench_delta.core.config import AgentProviderConfig
from githubbench_delta.core.models import AgentId, Difficulty, TaskCategory, TaskInput
from githubbench_delta.core.retry import RetryPolicy
from githubbench_delta.storage.events.jsonl_store import JSONLEventStore
from githubbench_delta.tasks.bug_fix import BugFixTask
from githubbench_delta.tools.base import ToolSpec
from githubbench_delta.trajectory.events import LifecycleStage


class ScriptedProvider(ProviderAdapter):
    """Deterministic provider for lifecycle tests (not a production fake answer)."""

    name = "scripted"

    def __init__(self, responses: list[ProviderResponse]) -> None:
        super().__init__(
            model="scripted",
            api_key=None,
            retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0, jitter=False),
        )
        self._responses = list(responses)
        self.calls = 0

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
    ) -> ProviderResponse:
        self.calls += 1
        if not self._responses:
            raise RuntimeError("No scripted responses left")
        return self._responses.pop(0)


class HarnessAgent(BaseAgent):
    """Minimal agent subclass for lifecycle testing."""


def _config() -> AgentProviderConfig:
    return AgentProviderConfig(
        id=AgentId.MINICPM,
        display_name="MiniCPM",
        provider="ollama",
        model="minicpm",
    )


@pytest.mark.asyncio
async def test_lifecycle_stages_and_cleanup_on_success(tmp_path: Path) -> None:
    store = JSONLEventStore(tmp_path / "events.jsonl")
    provider = ScriptedProvider(
        [
            ProviderResponse(
                text="The bug is an off-by-one in the loop.",
                usage=ProviderUsage(prompt_tokens=5, completion_tokens=7, total_tokens=12),
            )
        ]
    )
    agent = HarnessAgent(
        _config(),
        provider=provider,
        event_store=store,
        max_tool_calls=5,
    )
    task = BugFixTask(
        id="bug-lifecycle",
        category=TaskCategory.BUG_FIX,
        difficulty=Difficulty.EASY,
        input=TaskInput(prompt="Explain the off-by-one bug."),
    )
    result = await agent.run_task(task)

    assert result.success is True
    assert "off-by-one" in result.output.content
    assert result.trajectory is not None
    events = store.query(task_id="bug-lifecycle")
    stage_values = [e.stage for e in events]
    assert LifecycleStage.INITIALIZE in stage_values
    assert LifecycleStage.PREPARE_TASK in stage_values
    assert LifecycleStage.PLAN in stage_values
    assert LifecycleStage.PROVIDER in stage_values
    assert LifecycleStage.VALIDATE in stage_values
    assert LifecycleStage.CLEANUP in stage_values
    assert result.metrics.total_tokens == 12
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_lifecycle_cleanup_on_provider_failure(tmp_path: Path) -> None:
    from githubbench_delta.core.errors import FatalError

    class BoomProvider(ProviderAdapter):
        name = "boom"

        def __init__(self) -> None:
            super().__init__(model="x", api_key=None)

        async def complete(self, messages, tools) -> ProviderResponse:
            raise FatalError("provider down")

    store = JSONLEventStore(tmp_path / "events.jsonl")
    agent = HarnessAgent(
        _config(),
        provider=BoomProvider(),
        event_store=store,
    )
    task = BugFixTask(
        id="bug-fail",
        category=TaskCategory.BUG_FIX,
        input=TaskInput(prompt="fail please"),
    )
    result = await agent.run_task(task)
    assert result.success is False
    assert result.error is not None
    events = store.query(task_id="bug-fail")
    assert any(e.stage == LifecycleStage.CLEANUP for e in events)
    assert any(e.stage == LifecycleStage.INITIALIZE for e in events)


@pytest.mark.asyncio
async def test_tool_loop_with_scripted_provider(tmp_path: Path) -> None:
    from githubbench_delta.core.models import ToolCall

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "note.txt").write_text("secret-value-42\n", encoding="utf-8")

    provider = ScriptedProvider(
        [
            ProviderResponse(
                text="",
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="read_file",
                        arguments={"path": "note.txt"},
                    )
                ],
                raw={
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"note.txt"}',
                            },
                        }
                    ]
                },
                usage=ProviderUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            ),
            ProviderResponse(
                text="Found secret-value-42",
                usage=ProviderUsage(prompt_tokens=2, completion_tokens=2, total_tokens=4),
            ),
        ]
    )
    store = JSONLEventStore(tmp_path / "ev.jsonl")
    agent = HarnessAgent(_config(), provider=provider, event_store=store, max_tool_calls=5)
    task = BugFixTask(
        id="bug-tools",
        category=TaskCategory.BUG_FIX,
        input=TaskInput(
            prompt="Read note.txt",
            context={"repo_path": str(repo)},
        ),
    )
    result = await agent.run_task(task)
    assert result.success
    assert "secret-value-42" in result.output.content
    assert result.metrics.tool_call_count == 1
    events = store.query(task_id="bug-tools")
    assert any(e.stage == LifecycleStage.TOOL and e.tool == "read_file" for e in events)
