"""Execute tool calls against a ToolRegistry with timing."""

from __future__ import annotations

import time
from typing import Any

from githubbench_delta.core.errors import RegistryError, ToolExecutionError
from githubbench_delta.core.models import ToolCall, ToolResult
from githubbench_delta.tools.base import ToolContext
from githubbench_delta.tools.registry import ToolRegistry


class ToolExecutor:
    """Dispatch ``ToolCall`` instances to registered tools."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolContext,
    ) -> ToolResult:
        started = time.perf_counter()
        try:
            tool = self.registry.get(tool_call.name)
        except RegistryError as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

        try:
            output = await tool.execute(tool_call.arguments, context)
            duration_ms = (time.perf_counter() - started) * 1000
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
        except ToolExecutionError as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
                metadata={"fatal": exc.fatal, "tool_name": exc.tool_name or tool_call.name},
            )
        except Exception as exc:  # noqa: BLE001 — convert to ToolResult
            duration_ms = (time.perf_counter() - started) * 1000
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )

    async def execute_many(
        self,
        tool_calls: list[ToolCall],
        context: ToolContext,
    ) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in tool_calls:
            results.append(await self.execute(call, context))
        return results

    def provider_tool_schemas(self) -> list[dict[str, Any]]:
        """OpenAI-style function tool schemas."""

        schemas: list[dict[str, Any]] = []
        for spec in self.registry.specs():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.parameters,
                    },
                }
            )
        return schemas
