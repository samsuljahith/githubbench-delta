"""Configurable async retry with exponential backoff."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Sequence

from pydantic import BaseModel, Field

from githubbench_delta.core.errors import FatalError, RateLimitError, RecoverableError


class RetryPolicy(BaseModel):
    """Retry policy applied to provider and other recoverable operations."""

    max_attempts: int = Field(default=3, ge=1)
    base_delay_s: float = Field(default=0.5, ge=0.0)
    max_delay_s: float = Field(default=30.0, ge=0.0)
    exponential_base: float = Field(default=2.0, ge=1.0)
    jitter: bool = True
    retryable_exception_names: tuple[str, ...] = (
        "RecoverableError",
        "ProviderError",
        "RateLimitError",
        "ToolExecutionError",
    )

    def is_retryable(self, exc: BaseException) -> bool:
        """Return whether ``exc`` should trigger another attempt."""

        if isinstance(exc, FatalError):
            return False
        if isinstance(exc, RateLimitError | RecoverableError):
            return True
        return type(exc).__name__ in self.retryable_exception_names

    def delay_for_attempt(self, attempt: int) -> float:
        """Compute sleep duration before the next attempt (0-based attempt index)."""

        delay = min(
            self.max_delay_s,
            self.base_delay_s * (self.exponential_base**attempt),
        )
        if self.jitter and delay > 0:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


async def retry_async[T](
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> T:
    """Execute ``fn`` with exponential backoff per ``policy``.

    Args:
        fn: Zero-arg async callable.
        policy: Retry configuration.
        on_retry: Optional callback ``(attempt_index, exception, delay_s)``.

    Returns:
        Result of ``fn`` on success.

    Raises:
        The last exception if all attempts fail, or immediately if non-retryable.
    """

    last_exc: BaseException | None = None
    for attempt in range(policy.max_attempts):
        try:
            return await fn()
        except BaseException as exc:
            last_exc = exc
            if attempt >= policy.max_attempts - 1 or not policy.is_retryable(exc):
                raise
            delay = policy.delay_for_attempt(attempt)
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            if delay > 0:
                await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


def merge_retryable(
    policy: RetryPolicy,
    extra_names: Sequence[str],
) -> RetryPolicy:
    """Return a copy of ``policy`` with additional retryable exception names."""

    names = tuple(dict.fromkeys([*policy.retryable_exception_names, *extra_names]))
    return policy.model_copy(update={"retryable_exception_names": names})
