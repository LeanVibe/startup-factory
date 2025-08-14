import json
from pathlib import Path

from tools.dev import agent_runner


def test_agent_runner_cli_list_and_next(tmp_path, capsys):
    # Prepare a temp plan file (JSON to avoid YAML dependency)
    plan = {
        "version": 1,
        "plan": "phase_cli",
        "tasks": [
            {"name": "t1", "tests": ["pytest -q tests/unit/a.py::x"], "edits": [], "verify": [], "commit": "chore: t1"},
            {"name": "t2", "tests": ["pytest -q tests/unit/b.py::y"], "edits": [], "verify": [], "commit": "chore: t2"},
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    # Isolate state root to temp
    agent_runner.STATE_ROOT = tmp_path / ".agent_state"

    # --list prints task names only
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--list"])  # type: ignore[arg-type]
    assert rc == 0
    out = capsys.readouterr().out
    assert "t1" in out and "t2" in out

    # --next selects first not-done
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--next"])  # type: ignore[arg-type]
    assert rc == 0
    out = capsys.readouterr().out
    assert "Executing task: t1" in out or "Plan:" in out  # dry-run path prints Plan; execute path prints Executing
