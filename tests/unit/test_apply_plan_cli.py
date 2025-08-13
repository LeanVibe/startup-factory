from tools import apply_plan as ap


def test_summarize_plan_parses_actions_minimally():
    plan = {
        "actions": [
            {"type": "create", "path": "backend/app/foo.txt", "content": "hello"},
            {"type": "conflict", "path": "backend/app/bar.txt", "new_content": "world"},
        ]
    }
    summary = ap.summarize_plan(plan)
    assert summary["creates"] == 1
    assert summary["conflicts"] == 1


def test_apply_plan_dry_run_returns_summary_without_io():
    plan = {
        "actions": [
            {"type": "create", "path": "backend/app/foo.txt", "content": "hello"},
            {"type": "conflict", "path": "backend/app/bar.txt", "new_content": "world"},
        ]
    }
    # Dry run must not write; function should still return a summary
    result = ap.apply_plan(plan, project_root="/tmp/nonexistent-project-path", apply=False)
    assert result["creates"] == 1 and result["conflicts"] == 1
