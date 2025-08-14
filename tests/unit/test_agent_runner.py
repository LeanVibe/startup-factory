import textwrap


def test_agent_runner_summarize_plan_no_io():
    # We avoid YAML dependency in unit test; pass dict directly
    plan = {
        "version": 1,
        "plan": "phase_next",
        "tasks": [
            {
                "name": "epic-a-agent-runner",
                "tests": ["pytest -q tests/unit/test_agent_runner.py::will_fail_first"],
                "edits": ["add: tools/dev/agent_runner.py"],
                "verify": ["pytest -q tests/unit/test_agent_runner.py"],
                "commit": "feat(dev): add agent runner with dry-run and state markers",
            },
            {
                "name": "epic-b-seed-and-readme",
                "tests": ["pytest -q tests/unit/test_seed_and_readme.py::will_fail_first"],
                "edits": ["update: tools/manage.py"],
                "verify": ["pytest -q tests/unit/test_seed_and_readme.py"],
                "commit": "feat(dx): seed_basic_data/print_routes and README demo path",
            },
        ],
    }

    # Import locally to avoid hard dependency during discovery
    from tools.dev.agent_runner import summarize_plan_for_dry_run

    summary = summarize_plan_for_dry_run(plan)
    text = "\n".join(summary)

    # Basic structure checks
    assert "phase_next" in text
    assert "epic-a-agent-runner" in text
    assert "tests:" in text
    assert "edits:" in text
    assert "verify:" in text
    assert "commit:" in text

    # Order preserved
    first_idx = text.index("epic-a-agent-runner")
    second_idx = text.index("epic-b-seed-and-readme")
    assert first_idx < second_idx

    # Contains at least one test and one edit command
    assert "pytest -q tests/unit/test_agent_runner.py::will_fail_first" in text
    assert "add: tools/dev/agent_runner.py" in text
