import os
import sys
import types

import pytest

from startup_factory import StartupFactory


class StubDockerClient:
    def ping(self):
        return True


class StubDockerModule(types.SimpleNamespace):
    def from_env(self):
        return StubDockerClient()


@pytest.mark.parametrize(
    "has_key, expected",
    [
        (False, "❌ Missing"),
        (True, "✅ Ready"),
    ],
)
def test_system_status_reports_anthropic_key(capsys, monkeypatch, has_key, expected):
    # Control environment
    if has_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    else:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # Provide a stub docker module to avoid real dependency
    monkeypatch.setitem(sys.modules, "docker", StubDockerModule())

    sf = StartupFactory()
    sf.show_system_status()

    out = capsys.readouterr().out
    # Check Anthropic API row includes expected status
    assert "Anthropic API" in out
    assert expected in out
