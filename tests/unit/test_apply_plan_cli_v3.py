from tools import apply_plan
from pathlib import Path


def test_apply_plan_only_filter_and_summary():
    plan = {
        "actions": [
            {"type": "create", "path": "a.txt", "content": "a"},
            {"type": "update", "path": "b.txt", "new_content": "b"},
            {"type": "conflict", "path": "c.txt", "new_content": "c"},
        ]
    }
    # Only create should be applied
    root = Path("/tmp") / "plan_v3_test_root"
    res = apply_plan.apply_plan(plan, project_root=root, apply=True, only={"create"})
    # Should write only a.txt, not .new for b/c
    assert any(str(p).endswith("a.txt") for p in res)
    assert not any(str(p).endswith("b.txt.new") for p in res)
    assert not any(str(p).endswith("c.txt.new") for p in res)

    # Summary generation
    summary = apply_plan.summarize_plan(plan)
    assert summary["creates"] == 1 and summary["updates"] == 1 and summary["conflicts"] == 1
