#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List


@dataclass
class PlanAction:
    type: str
    path: str


def summarize_plan(plan: Dict[str, Any]) -> str:
    actions = plan.get("actions", [])
    creates = sum(1 for a in actions if a.get("type") == "create")
    conflicts = sum(1 for a in actions if a.get("type") == "conflict")
    updates = sum(1 for a in actions if a.get("type") == "update")
    return f"create: {creates}, update: {updates}, conflict: {conflicts}"


def apply_plan(project_dir: str, plan: Dict[str, Any], do_apply: bool = False) -> List[Path]:
    project_path = Path("production_projects") / project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for action in plan.get("actions", []):
        action_type = action.get("type")
        rel_path = action.get("path")
        if not rel_path:
            continue
        target = project_path / rel_path

        if action_type == "create":
            if do_apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("")
                written.append(target)
        elif action_type == "conflict":
            if do_apply:
                conflict_path = target.with_suffix(target.suffix + ".new")
                conflict_path.parent.mkdir(parents=True, exist_ok=True)
                conflict_path.write_text("")
                written.append(conflict_path)
        # ignore updates for now (safe)
    return written


def main():
    parser = argparse.ArgumentParser(description="Apply safe plan actions to a project")
    parser.add_argument("project", help="Project directory name under production_projects/")
    parser.add_argument("--plan", dest="plan_path", default=None, help="Path to plan.json (defaults to project dir)")
    parser.add_argument("--apply", dest="apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    project = args.project
    plan_file = Path(args.plan_path) if args.plan_path else (Path("production_projects") / project / "plan.json")
    if not plan_file.exists():
        print(f"Plan file not found: {plan_file}")
        return 1

    plan = json.loads(plan_file.read_text())
    summary = summarize_plan(plan)
    print(summary)

    if args.apply:
        written = apply_plan(project, plan, do_apply=True)
        for p in written:
            print(f"wrote: {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
