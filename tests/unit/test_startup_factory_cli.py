import asyncio
import sys

import pytest

import startup_factory as sf_module
from startup_factory import StartupFactory


@pytest.mark.asyncio
async def test_cli_status_calls_show_system_status(monkeypatch, capsys):
    called = {"status": False}

    def fake_status(self):
        called["status"] = True
        print("STATUS_CALLED")

    monkeypatch.setattr(StartupFactory, "show_system_status", fake_status, raising=True)

    argv_backup = sys.argv[:]
    sys.argv = [argv_backup[0], "--status"]
    try:
        await sf_module.main()
    finally:
        sys.argv = argv_backup

    out = capsys.readouterr().out
    assert called["status"] is True
    assert "STATUS_CALLED" in out


@pytest.mark.asyncio
async def test_cli_demo_calls_show_demonstration(monkeypatch, capsys):
    called = {"demo": False}

    def fake_demo(self):
        called["demo"] = True
        print("DEMO_CALLED")

    monkeypatch.setattr(StartupFactory, "show_demonstration", fake_demo, raising=True)

    argv_backup = sys.argv[:]
    sys.argv = [argv_backup[0], "--demo"]
    try:
        await sf_module.main()
    finally:
        sys.argv = argv_backup

    out = capsys.readouterr().out
    assert called["demo"] is True
    assert "DEMO_CALLED" in out


@pytest.mark.asyncio
async def test_cli_help_prints_options(capsys):
    argv_backup = sys.argv[:]
    sys.argv = [argv_backup[0], "--help"]
    try:
        await sf_module.main()
    finally:
        sys.argv = argv_backup

    out = capsys.readouterr().out
    assert "Command Line Options" in out
    assert "--status" in out
    assert "--demo" in out


@pytest.mark.asyncio
async def test_cli_unknown_option_prints_error(capsys):
    argv_backup = sys.argv[:]
    sys.argv = [argv_backup[0], "--unknown"]
    try:
        await sf_module.main()
    finally:
        sys.argv = argv_backup

    out = capsys.readouterr().out
    assert "Unknown option" in out
    assert "Use --help" in out
