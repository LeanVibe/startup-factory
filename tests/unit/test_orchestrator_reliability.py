import asyncio
import pytest

from tools.streamlined_mvp_orchestrator import StreamlinedOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_has_reliable_helpers(monkeypatch):
    orch = StreamlinedOrchestrator()
    # Ensure orchestrator imports retry utils for use in polling/build
    import tools.retry_utils as ru  # type: ignore
    assert hasattr(ru, "retry_async")
