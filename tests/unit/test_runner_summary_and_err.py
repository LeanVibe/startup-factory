import json
from pathlib import Path

from tools.dev import agent_runner


def test_runner_dry_run_summary_and_err_markers(tmp_path, capsys):
    plan = {
        "version": 1,
        "plan": "p1",
        "tasks": [
            {"name": "a", "tests": ["echo a"], "verify": ["echo v"], "commit": "c"},
            {"name": "b", "tests": ["echo b"], "verify": ["echo v"], "commit": "c"},
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    agent_runner.STATE_ROOT = tmp_path / ".agent_state"
    agent_runner.LOG_ROOT = tmp_path / ".agent_state/logs"
    # mark first done
    (agent_runner.STATE_ROOT / "p1").mkdir(parents=True, exist_ok=True)
    (agent_runner.STATE_ROOT / "p1" / "a.done").write_text("done\n")

    # Dry-run prints summary and next
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--dry-run"])  # type: ignore[arg-type]
    assert rc == 0
    out = capsys.readouterr().out
    assert "SUMMARY" in out and "[pending] b" in out and "next: b" in out

    # Execute a failure for b
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--execute", "--next", "--simulate-failure"])  # type: ignore[arg-type]
    assert rc == 0
    assert (agent_runner.STATE_ROOT / "p1" / "b.err").exists()
