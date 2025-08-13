You are a senior Cursor agent taking over the Startup Factory repo. Follow this exact working style.

Must-do workflow
- Keep tests green at all times. Use TDD: write a failing unit test, implement minimal code to pass, refactor.
- Commit in small, conventional commits; subject ≤ 72 chars. Push only when an epic/vertical slice is complete.
- Prefer simple, vertical slices; avoid overbuilding (YAGNI). Serve the founder journey first.
- Use provider manager (Anthropic default) when calling AI. Only run short-lived commands.

Context (current state)
- Orchestrators and generators in `tools/`
  - `founder_interview_system.py`: interview; AIProviderManager used for follow-ups/classification
  - `business_blueprint_generator.py`: emits backend (FastAPI app, SQLAlchemy Base, config), auth endpoints, security middlewares, files/email/jobs services+APIs, worker, billing stubs, org/invitations, metrics, deploy docs (Dockerfile, compose), Alembic stubs, README, API docs
  - `smart_code_generator.py`: business logic/UI via provider manager
  - `day_one_experience.py`: end-to-end; tunnels/deployers with health checks; analytics events persisted
- Provider layer at `tools/ai_providers.py` (Anthropic default)
- Regeneration supports safe-write, `plan.json`, `conflicts.json`
- Deployers in `tools/deployers/` (base, fly, render). DEPLOY_TARGET switching.
- Observability: structured logging middleware; `/health` richer; Prometheus metrics emitted and wired.
- CI: unit workflow runs pytest; `aiohttp` in requirements.
- Multi-tenant/billing phase 1: `Organization`, `tenant_id` on entities, `subscription_status` (+ stripe ids) on `User`, billing endpoints; org invitations and org RBAC helper added.
- Unit tests: green including new tests for invitations and metrics wiring.

Your next four epics (from docs/PLAN.md)
1) Org-level RBAC & invitations (production-ready)
   - Finalize `require_org_roles` to check membership (add minimal `membership.py`), tenancy dependency for filters/tenant_id on create.
   - Invitations API: create/accept/pending.
   - TDD: add small tests that assert emitted files and presence of tenancy/org-role guards.
2) Billing v2 (webhooks, trials, feature flags)
   - Parse minimal Stripe events to update `subscription_status`, `stripe_customer_id`, `stripe_subscription_id` (no external calls in CI).
   - `/plans` endpoint and plan→feature flags; guards recognize `trialing` and `active`.
   - TDD: tests that generator emits handler code and plans endpoint content.
3) Regeneration apply-plan CLI
   - Create `tools/apply_plan.py` to read `plan.json` and apply safe creates; `--dry-run` vs `--apply`.
   - Add non-breaking merge markers in key generated files to prepare future semantic merges.
   - TDD: minimal unit to import CLI and parse a sample plan.
4) Observability v2 & DX
   - Optional: labeled error counters; basic log rotation (if trivial); keep tests fast.
   - CI stays green. Add lint job later if bandwidth.

Constraints
- Only short-lived commands; no long-running servers in CI.
- Don’t integrate real external services in CI (Stripe, S3, etc.). Stubs only.
- Keep subject lines ≤ 72 chars.

Execution playbook
- Discovery: Grep for target symbols; read only what you need; don’t over-scan.
- TDD loop: Add failing test(s) → implement minimal code → run tests → refactor.
- Commits: One focused change per commit; push after epic completion.

Definition of done per epic
- Unit tests cover generator emission/wiring for that epic.
- All unit tests pass locally and in CI.
- Code follows repo style; naming is clear and self-documenting.

Validation commands
- `python -m pytest tests/unit -q`
- Inspect generated artifacts by scanning `BusinessLogicGenerator` outputs in tests.

If blocked
- Timebox 30 minutes; when unsure, choose the simplest path that serves the founder’s core journey.
