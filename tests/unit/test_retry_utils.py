import asyncio
import time

import pytest

from tools import retry_utils


def test_compute_backoff_ms_with_jitter_bounds():
    base_ms = 100
    max_ms = 2000
    seq = [retry_utils.compute_backoff_ms_with_jitter(base_ms, attempt, max_ms) for attempt in range(1, 6)]
    # monotonic non-decreasing (allow equal)
    assert all(seq[i] <= seq[i+1] for i in range(len(seq)-1))
    # within max cap
    assert max(seq) <= max_ms


@pytest.mark.asyncio
async def test_retry_async_succeeds_on_second_attempt():
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("boom")
        return "ok"

    result = await retry_utils.retry_async(flaky, max_attempts=3, base_delay_ms=10, max_delay_ms=50)
    assert result == "ok"
    assert attempts["count"] == 2
