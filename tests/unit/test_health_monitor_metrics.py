from tools.ai_providers import AIProviderManager, ProviderCall


def test_error_category_counts_from_call_history():
    m = AIProviderManager()
    # populate all_calls with various errors
    import datetime

    now = datetime.datetime.utcnow()
    m.all_calls.extend(
        [
            ProviderCall(
                provider="anthropic",
                task_id="t1",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0.0,
                timestamp=now,
                success=False,
                error="timeout",
            ),
            ProviderCall(
                provider="anthropic",
                task_id="t2",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0.0,
                timestamp=now,
                success=False,
                error="rate limit exceeded",
            ),
            ProviderCall(
                provider="anthropic",
                task_id="t3",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0.0,
                timestamp=now,
                success=False,
                error="unauthorized",
            ),
            ProviderCall(
                provider="anthropic",
                task_id="t4",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0.0,
                timestamp=now,
                success=False,
                error="out of memory",
            ),
            ProviderCall(
                provider="anthropic",
                task_id="t5",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0.0,
                timestamp=now,
                success=False,
                error="dns failure",
            ),
        ]
    )
    counts = m.get_error_category_counts()
    assert counts.get("timeout") == 1
    assert counts.get("rate_limit") == 1
    assert counts.get("auth") == 1
    assert counts.get("oom") == 1
    assert counts.get("network") == 1
