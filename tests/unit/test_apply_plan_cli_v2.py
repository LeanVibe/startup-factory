from tools import apply_plan
from pathlib import Path
import uuid


def test_apply_plan_writes_new_for_update_and_conflict(tmp_path: Path):
    project = f"ep3_{uuid.uuid4().hex[:8]}"
    plan = {
        "actions": [
            {"type": "create", "path": "a.txt"},
            {"type": "update", "path": "b.txt"},
            {"type": "conflict", "path": "c.txt"},
        ]
    }
    written = apply_plan.apply_plan(project, plan, do_apply=True)
    written_paths = {Path(p).name if isinstance(p, (str,)) else p.name for p in written}

    base = Path("production_projects") / project
    assert (base / "a.txt").exists(), "create should write plain file"
    assert any(name.startswith("b.txt") and name.endswith(".new") for name in written_paths) or (base / "b.txt.new").exists()
    assert any(name.startswith("c.txt") and name.endswith(".new") for name in written_paths) or (base / "c.txt.new").exists()
