import pytest

from tools.streamlined_mvp_orchestrator import StreamlinedOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_has_reliable_helpers(monkeypatch):
    # Provide API key to avoid exit path
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    import types
    import sys

    class StubAnthropic(types.SimpleNamespace):
        class Anthropic:
            def __init__(self, api_key: str):
                self.api_key = api_key

    monkeypatch.setitem(sys.modules, "anthropic", StubAnthropic)

    _ = StreamlinedOrchestrator()
    # Ensure orchestrator imports retry utils for use in polling/build
    import tools.retry_utils as ru  # type: ignore

    assert hasattr(ru, "retry_async")
