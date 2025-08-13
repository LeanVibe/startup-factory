from tools import apply_plan


def test_apply_plan_summarize_minimal_plan():
    plan = {
        "actions": [
            {"type": "create", "path": "a.txt"},
            {"type": "create", "path": "b.txt"},
            {"type": "conflict", "path": "c.txt"},
        ]
    }
    summary = apply_plan.summarize_plan(plan)
    assert isinstance(summary, str)
    assert "create: 2" in summary
    assert "conflict: 1" in summary
