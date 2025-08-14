import json

from tools.dev import agent_runner


def test_agent_runner_max_parallel_logged(tmp_path, capsys):
    plan = {
        "version": 1,
        "plan": "p",
        "tasks": [
            {"name": "t1", "tests": ["echo 1"], "verify": ["echo v"], "commit": "c"}
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    agent_runner.STATE_ROOT = tmp_path / ".agent_state"
    agent_runner.LOG_ROOT = tmp_path / ".agent_state/logs"

    rc = agent_runner.run_cli(
        ["--plan", str(plan_path), "--execute", "--next", "--max-parallel", "3"]
    )  # type: ignore[arg-type]
    assert rc == 0
    logs = list((tmp_path / ".agent_state/logs").glob("*.log"))
    txt = logs[0].read_text()
    assert "max_parallel: 3" in txt
