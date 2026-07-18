"""Retry policy tests."""

from __future__ import annotations

import pytest

from githubbench_delta.core.errors import FatalError, ProviderError, RateLimitError
from githubbench_delta.core.retry import RetryPolicy, retry_async


@pytest.mark.asyncio
async def test_retry_succeeds_after_recoverable_failures() -> None:
    attempts = {"n": 0}

    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ProviderError("transient")
        return "ok"

    policy = RetryPolicy(max_attempts=3, base_delay_s=0.0, jitter=False)
    assert await retry_async(flaky, policy) == "ok"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_fatal_error_not_retried() -> None:
    attempts = {"n": 0}

    async def boom() -> None:
        attempts["n"] += 1
        raise FatalError("stop")

    policy = RetryPolicy(max_attempts=5, base_delay_s=0.0, jitter=False)
    with pytest.raises(FatalError):
        await retry_async(boom, policy)
    assert attempts["n"] == 1


def test_rate_limit_is_retryable() -> None:
    policy = RetryPolicy()
    assert policy.is_retryable(RateLimitError("slow down"))
    assert policy.delay_for_attempt(0) >= 0
    assert policy.delay_for_attempt(2) >= policy.delay_for_attempt(0) or policy.jitter
