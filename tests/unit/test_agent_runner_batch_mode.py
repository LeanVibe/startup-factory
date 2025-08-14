import json
from pathlib import Path

from tools.dev import agent_runner


def test_agent_runner_instructions_logged(tmp_path, capsys):
    plan = {
        "version": 1,
        "plan": "phase_batch",
        "tasks": [
            {"name": "t1", "tests": ["echo test"], "edits": [], "verify": ["echo verify"], "commit": "chore: t1"},
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    instr_file = tmp_path / "instructions.txt"
    instr_file.write_text("Do X then Y")

    # Point state/logs to a temp dir
    agent_runner.STATE_ROOT = tmp_path / ".agent_state"
    agent_runner.LOG_ROOT = tmp_path / ".agent_state/logs"

    # Dry-run echoes instructions path in output
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--dry-run", "--instructions", str(instr_file)])  # type: ignore[arg-type]
    assert rc == 0
    out = capsys.readouterr().out
    assert "Plan:" in out

    # Execute logs file content
    rc = agent_runner.run_cli(["--plan", str(plan_path), "--execute", "--next", "--instructions", str(instr_file), "--subagent", "tester"])  # type: ignore[arg-type]
    assert rc == 0
    # Check log file content
    logs = list((tmp_path / ".agent_state/logs").glob("*.log"))
    assert logs, "expected a per-task log file"
    log_text = logs[0].read_text()
    assert "instructions:" in log_text and "Do X then Y" in log_text and "subagent: tester" in log_text
