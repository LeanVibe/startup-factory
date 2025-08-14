# Orchestration: Plan → Batch → Verify (Cursor/CLI Friendly)

This guide describes a resilient way to run longer, uninterrupted work in short batches without holding a session open.

## Workflow
- Author a small YAML plan that encodes tasks as: tests → edits → verify → commit.
- Dry-run to see all steps, then execute in small batches.
- State markers are written under `.agent_state/<plan>/<task>.done` so you can resume.

## Plan schema (v1)
```yaml
version: 1              # required
plan: <name>            # required, used for .agent_state/<plan>
tasks:                  # required
  - name: <task-name>   # required
    tests: [<cmd>...]   # optional (list of short-lived cmds)
    edits: [<hint>...]  # optional (notes for human/agent)
    verify: [<cmd>...]  # optional
    commit: <message>   # optional, conventional summary
```

## Commands
```bash
# Preview steps
python tools/dev/agent_runner.py --plan plans/phase_next.yaml --dry-run

# Execute the next not-done task
python tools/dev/agent_runner.py --plan plans/phase_next.yaml --next --execute

# List task names
python tools/dev/agent_runner.py --plan plans/phase_next.yaml --list

# Resume (alias for --next)
python tools/dev/agent_runner.py --plan plans/phase_next.yaml --resume --execute
```

## Good task hygiene
- Keep each task ≤ 5 minutes. Prefer string-assert tests, no network.
- Make tasks idempotent. Reruns should be safe.
- Avoid long-lived processes; use non-interactive status checks.
- Persist prompt/decisions in `docs/` and state in `.agent_state/`.

## Example plan
See `plans/phase_next.yaml` for a ready-to-run example.
