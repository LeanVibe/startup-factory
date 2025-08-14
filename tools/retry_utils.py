"""
Retry utilities for short-lived, deterministic retries with backoff and jitter.
"""
from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def compute_backoff_ms_with_jitter(base_delay_ms: int, attempt: int, max_delay_ms: int) -> int:
    # Exponential backoff with full jitter, capped. Ensure non-decreasing expected value.
    exp = base_delay_ms * (2 ** (attempt - 1))
    cap = min(max_delay_ms, exp)
    jitter = random.randint(cap // 2, cap)  # half-to-full jitter range to avoid very small regressions
    return min(max_delay_ms, max(jitter, base_delay_ms))


async def retry_async(fn: Callable[[], Awaitable[T]], max_attempts: int = 3, base_delay_ms: int = 100, max_delay_ms: int = 2000) -> T:
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as e:  # pragma: no cover - error paths are covered via tests
            last_err = e
            if attempt >= max_attempts:
                break
            delay_ms = compute_backoff_ms_with_jitter(base_delay_ms, attempt, max_delay_ms)
            await asyncio.sleep(delay_ms / 1000.0)
    assert last_err is not None
    raise last_err
