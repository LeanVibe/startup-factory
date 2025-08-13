from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Union


def summarize_plan(plan: Dict[str, Any]) -> Dict[str, int]:
    actions = plan.get("actions") or []
    creates = sum(1 for a in actions if (a.get("type") == "create"))
    conflicts = sum(1 for a in actions if (a.get("type") == "conflict"))
    updates = sum(1 for a in actions if (a.get("type") == "update"))
    return {"creates": creates, "conflicts": conflicts, "updates": updates}


def apply_plan(
    plan_or_project: Union[Dict[str, Any], str, Path],
    project_or_plan: Union[Dict[str, Any], str, Path, None] = None,
    *,
    apply: bool = False,
    do_apply: bool = False,
    project_root: Union[str, Path, None] = None,
):
    """Apply a generation plan.

    Compatibility:
    - Style A: apply_plan(plan, project_root=..., apply=True|False)
    - Style B: apply_plan(project_name, plan, do_apply=True|False)
    """
    # Determine plan and root path
    detected_plan: Dict[str, Any]
    detected_project: Union[str, Path, None] = None

    if isinstance(plan_or_project, dict):
        detected_plan = plan_or_project
        detected_project = project_or_plan if isinstance(project_or_plan, (str, Path)) else None
    elif isinstance(project_or_plan, dict):
        detected_plan = project_or_plan  # first arg is project
        detected_project = plan_or_project
    else:
        detected_plan = {"actions": []}
        detected_project = plan_or_project if isinstance(plan_or_project, (str, Path)) else None

    # Resolve root
    if project_root is not None:
        root = Path(project_root)
    else:
        if detected_project is None:
            root = Path(".")
        else:
            proj = Path(str(detected_project))
            # If not absolute, write under production_projects/<project>
            root = proj if proj.is_absolute() else Path("production_projects") / proj

    summary = summarize_plan(detected_plan)
    do_write = bool(apply or do_apply)
    if not do_write:
        return summary
    # Only perform safe creates; write files that don't exist yet
    written_paths = []
    for action in detected_plan.get("actions", []):
        if action.get("type") == "create":
            path = root / action.get("path", "")
            content = action.get("content", "")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(content)
            written_paths.append(str(path))
        elif action.get("type") == "conflict":
            # leave a .new file alongside the original path
            base = root / action.get("path", "")
            new_path = base.with_suffix(base.suffix + ".new")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(action.get("new_content", ""))
            written_paths.append(str(new_path))
        elif action.get("type") == "update":
            # do not overwrite; write side-by-side .new for manual merge
            base = root / action.get("path", "")
            new_path = base.with_suffix(base.suffix + ".new")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(action.get("new_content", action.get("content", "")))
            written_paths.append(str(new_path))
        # 'update' is intentionally skipped in auto-apply mode
    return written_paths or summary


if __name__ == "__main__":
    import argparse, json, sys
    p = argparse.ArgumentParser(description="Apply a generation plan safely")
    p.add_argument("project", help="project directory containing plan.json")
    p.add_argument("--apply", action="store_true", help="perform writes; default dry-run")
    args = p.parse_args()
    project_dir = Path(args.project)
    plan_path = project_dir / "plan.json"
    data = json.loads(plan_path.read_text()) if plan_path.exists() else {"actions": []}
    res = apply_plan(data, project_root=project_dir, apply=args.apply)
    print(json.dumps({"summary": res}, indent=2))
