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
- Multi-tenant/billing phase 1+2: `Organization`, `tenant_id` on entities, `subscription_status` (+ stripe ids) on `User`, billing endpoints; plan→features mapping; trials recognized.
- Unit tests: green including new tests for invitations, metrics wiring, flags/logging, billing v2, apply-plan CLI, day-one metadata, observability v2.

Recent changes you should know
- Feature flags: `backend/app/core/feature_flags.py` and usage in entity create
- Logging: PII redaction for Authorization/cookies; HSTS + OpenAPI bearer placeholder in `main.py`
- Org RBAC: invitations/admin routers included; tenancy dependency on update
- Billing v2: PLAN_FEATURES mapping; `trialing` accepted; webhook events handled in stubs
- Apply-plan CLI: `tools/apply_plan.py` with dry-run and safe apply; compatibility for two call styles
- Observability v2: metrics wiring and rotation hook tests
- Deployment slice: Day One writes `production_projects/<id>/project.json`; deployer selection validated; Docker fallback for tests

Your next four epics (from docs/PLAN.md)
1) Auth/session & security v2 (JWT/OpenAPI/cookie‑CSRF)
   - Add OAuth2 password flow placeholder and global security requirement to `backend/app/main.py` (commented/conditional).
   - Ensure CSRF path is clear for cookie mode; add minimal password policy checks; consistent `HTTPBearer` imports.
   - TDD: tests assert OpenAPI additions, cookie mode notes, and consistent imports.
2) Compliance toggles (industry‑aware scaffolds)
   - Add HIPAA/PCI/FERPA toggles in `core/config.py`; expand redaction headers when toggles set.
   - Emit compliance comments in security middleware/services based on industry.
   - TDD: tests assert flags/comments exist for healthcare/fintech/education.
3) Generated app quality gates (smoke + security checks)
   - Emit tests for security headers, `/metrics`, and redaction; add `tools/manage.py` helper (no external IO).
   - TDD: tests assert artifacts emitted.
4) Deployment polish (optional Railway, tunnels ergonomics)
   - Add RailwayDeployer stub and wire selection; improve tunnel detection messages.
   - TDD: deployer selection includes railway; metadata persists unchanged.

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

Kickoff checklist for you
- Read `docs/PLAN.md` (updated) and this prompt.
- Run unit tests. Ensure 100% pass.
- Start Epic 2 (Auth/security v2):
  - Add failing unit tests under `tests/unit/` for OpenAPI oauth2+global security and cookie mode notes.
  - Implement minimal generator edits to satisfy tests.
  - Keep changes comment/conditional where appropriate to avoid runtime breakage.
- Proceed to Epic 3 and 4 similarly, one vertical slice at a time.

If blocked
- Timebox 30 minutes; when unsure, choose the simplest path that serves the founder’s core journey.
