#!/usr/bin/env python3
"""
Agent Runner — plan → batch → verify loop executor (dry-run by default).

- Loads a YAML plan (or accepts a dict) with tasks: tests → edits → verify → commit
- Maintains idempotent markers under `.agent_state/<plan>/<task>.done`
- Provides summarize function for tests without filesystem or YAML dependency

CLI (lightweight):
  python tools/dev/agent_runner.py --plan plans/phase_next.yaml --dry-run
  python tools/dev/agent_runner.py --plan plans/phase_next.yaml --execute

The unit tests use summarize_plan_for_dry_run(dict) to avoid IO.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # Optional for CLI; tests don't require
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

STATE_ROOT = Path('.agent_state')
LOG_ROOT = Path('.agent_state/logs')


def summarize_plan_for_dry_run(plan: Dict[str, Any]) -> List[str]:
    """Return a human-readable summary of ordered steps for dry-run.

    No filesystem or YAML access; pure function used by unit tests.
    """
    lines: List[str] = []
    version = plan.get('version', 'unknown')
    plan_name = plan.get('plan', 'unnamed_plan')
    lines.append(f"Plan: {plan_name} (version {version})")
    lines.append("")

    tasks = plan.get('tasks', [])
    for idx, task in enumerate(tasks, start=1):
        name = task.get('name', f'task_{idx}')
        lines.append(f"- {name}")
        for key in ('tests', 'edits', 'verify', 'commit'):
            value = task.get(key)
            if value is None:
                continue
            if key == 'commit':
                lines.append(f"  commit: {value}")
            else:
                lines.append(f"  {key}:")
                for entry in value:
                    lines.append(f"    - {entry}")
        lines.append("")
    return lines


def _marker_path(plan_name: str, task_name: str) -> Path:
    return STATE_ROOT / plan_name / f"{task_name}.done"


def _is_task_done(plan_name: str, task_name: str) -> bool:
    return _marker_path(plan_name, task_name).exists()


def _mark_task_done(plan_name: str, task_name: str) -> None:
    marker = _marker_path(plan_name, task_name)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("done\n")


def _load_plan_from_yaml(path: Path) -> Dict[str, Any]:  # pragma: no cover (CLI only)
    if yaml is None:
        raise RuntimeError("PyYAML not available; cannot load plan from file")
    with path.open() as f:
        data = yaml.safe_load(f)
    # Minimal schema validation
    if not isinstance(data, dict) or 'version' not in data or 'plan' not in data or 'tasks' not in data:
        raise SystemExit('Invalid plan schema: require version, plan, tasks')
    if not isinstance(data['tasks'], list):
        raise SystemExit('Invalid plan schema: tasks must be a list')
    return data


def _print(lines: List[str]) -> None:  # separated for testability
    for ln in lines:
        print(ln)


def run_cli(argv: Optional[List[str]] = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Agent Runner (dry-run by default)")
    parser.add_argument('--plan', type=str, required=False, help='Path to YAML plan file')
    parser.add_argument('--dry-run', action='store_true', help='Print steps, do not execute')
    parser.add_argument('--execute', action='store_true', help='Execute steps and write state markers')
    parser.add_argument('--only', type=str, help='Run single task by name')
    parser.add_argument('--next', dest='next_task', action='store_true', help='Run the next not-done task')
    parser.add_argument('--list', dest='list_tasks', action='store_true', help='List tasks and exit')
    parser.add_argument('--resume', dest='next_task_alias', action='store_true', help='Alias for --next')
    parser.add_argument('--instructions', type=str, help='Path to an instructions file to log alongside execution')
    parser.add_argument('--subagent', type=str, choices=['tester','editor','verifier'], help='Delegate execution hint (logged only)')
    args = parser.parse_args(argv)

    plan: Dict[str, Any]
    if args.plan:
        plan = _load_plan_from_yaml(Path(args.plan))
    else:
        raise SystemExit('--plan is required for CLI usage')

    plan_name = plan.get('plan', 'unnamed_plan')
    tasks: List[Dict[str, Any]] = plan.get('tasks', [])

    # Filter tasks if needed
    if args.only:
        tasks = [t for t in tasks if t.get('name') == args.only]
        if not tasks:
            print(f"No task named {args.only} in plan {plan_name}")
            return 1

    if args.list_tasks:
        for t in tasks:
            print(t.get('name', 'unnamed_task'))
        return 0

    if args.next_task or args.next_task_alias:
        tasks = [t for t in tasks if not _is_task_done(plan_name, t.get('name', ''))]
        if not tasks:
            print('All tasks already completed.')
            return 0
        tasks = [tasks[0]]

    if args.dry_run or not args.execute:
        _print(summarize_plan_for_dry_run(plan))
        return 0

    # Execute mode (lightweight): we only create markers; actual commands are printed
    for task in tasks:
        name = task.get('name', 'unnamed_task')
        print(f"Executing task: {name}")
        # per-task log
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        logf = (LOG_ROOT / f"{plan_name}__{name}.log").open('a')
        # log instructions/subagent hints once at top
        if args.instructions:
            try:
                content = Path(args.instructions).read_text()
                logf.write(f"instructions: {content}\n")
            except Exception:
                logf.write("instructions: <unreadable>\n")
        if args.subagent:
            logf.write(f"subagent: {args.subagent}\n")

        for phase in ('tests', 'edits', 'verify'):
            cmds = task.get(phase, [])
            if cmds:
                print(f"# {phase}")
                for cmd in cmds:
                    print(cmd)
                    try:
                        logf.write(f"{phase}: {cmd}\n")
                    except Exception:
                        pass
        if task.get('commit'):
            print(f"# commit\n{task['commit']}")
            try:
                logf.write(f"commit: {task['commit']}\n")
            except Exception:
                pass
        _mark_task_done(plan_name, name)
        print(f"Marked done: {name}")
        try:
            logf.close()
        except Exception:
            pass

    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(run_cli())
