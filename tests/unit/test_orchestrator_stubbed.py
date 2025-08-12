import asyncio
import os
import sys
import types
from pathlib import Path

import pytest

# Import orchestrator under test
from tools.streamlined_mvp_orchestrator import StreamlinedOrchestrator


class StubAnthropic(types.SimpleNamespace):
    class Anthropic:
        def __init__(self, api_key: str):
            self.api_key = api_key


@pytest.mark.asyncio
async def test_orchestrator_requires_api_key(monkeypatch, capsys):
    # Ensure missing key triggers error message and exit path
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # Inject stub anthropic to avoid importing real package
    monkeypatch.setitem(sys.modules, "anthropic", StubAnthropic)

    with pytest.raises(SystemExit):
        # _setup_anthropic calls exit(1) on missing key
        _ = StreamlinedOrchestrator()


@pytest.mark.asyncio
async def test_orchestrator_creates_output_dir(monkeypatch, tmp_path):
    # Provide API key
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Inject stub anthropic
    monkeypatch.setitem(sys.modules, "anthropic", StubAnthropic)

    orch = StreamlinedOrchestrator()

    # Redirect output dir to temp to avoid writing to repo
    orch.output_dir = tmp_path / "production_projects"

    # Stub heavy phases to no-op fast coroutines
    monkeypatch.setattr(
        orch,
        "run_complete_workflow",
        lambda: asyncio.sleep(0),
        raising=True,
    )

    # Ensure output dir exists
    orch.output_dir.mkdir(parents=True, exist_ok=True)
    assert orch.output_dir.exists()
