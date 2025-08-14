# Delivery Plan – Next Four Epics (Deployment, Auth/Security v2, Compliance, Quality Gates)

This plan captures the immediate next four epics, their deliverables, tests (TDD), and acceptance criteria. It reflects the current repository state and extends it toward a fully production‑oriented founder workflow.

## Current status (done)
- Security/auth: JWT helpers, reset/verify flows, optional TOTP + cookie mode scaffolds
- RBAC: `backend/app/core/rbac.py`, role on `User`, guards on generated endpoints
- Files/email/jobs: S3 storage service, files API (`/files/upload`, `/files/sign-upload`), SMTP email, RQ worker & jobs API
- Deployers: `tools/deployers/{base,fly,render}.py` and DEPLOY_TARGET wiring in Day One
- Regeneration: safe-write and `plan.json`/`conflicts.json` outputs; `tools/apply_plan.py` with dry‑run/safe apply
- Multi-tenant/billing: `Organization`, `tenant_id` on entities, `subscription_status` on `User`, billing service & endpoints, plan→features mapping and trialing
- Observability: Structured logging middleware; richer `/health`; Prometheus metrics emitted and wired (`init_metrics(app)`); rotation hook test
- Deployment metadata: Day One writes `production_projects/<id>/project.json`; deployer selection validated; Docker fallback in tests

---

## Epic 1 — Production deployment with live URLs

### Goals
- Allow founders to get a public URL deterministically via tunnels or stubbed cloud deployers.
- Persist deployment metadata for later iteration.

### Deliverables
- Deployer selection: `tools/deployers.get_deployer` (fly, render; base fallback) [done]
- Day One metadata persistence: `project.json` written with `public_url`, `deployer`, timestamps [done]
- Public access: cloudflared/ngrok optional tunnel start; fallback to `http://localhost:8000` [partial]
- Add RailwayDeployer stub in `tools/deployers/railway.py` and wire into `get_deployer` (optional)

### Tests (TDD)
- Unit: deployer selection returns expected classes
- Unit: `_write_project_metadata` writes `project.json` with `public_url` and `deployer`

### Acceptance
- Running Day One (interactive or mocked) results in persisted metadata and an accessible URL (local/tunnel/stub).

---

## Epic 2 — Auth/session & security v2 (JWT/OpenAPI/cookie‑CSRF)

### Goals
- Ensure consistent auth across routers, better OpenAPI definition, and stricter defaults for cookie mode.

### Deliverables
- OpenAPI: add OAuth2 password flow placeholder and global `security` requirement in `backend/app/main.py` (commented or conditional)
- CSRF: enforce cookie‑mode CSRF path in `middleware/csrf.py` (already present) and ensure auth endpoints clearly document cookie mode
- Rate limits: lightweight per‑route override facility using existing RateLimit middleware (route label or header check)
- Password policy: minimal length/complexity check on registration (non‑blocking in CI)

### Tests (TDD)
- Unit: `main.py` contains oauth2 scheme block and global `security` requirement placeholder
- Unit: auth endpoints mention cookie mode/CSRF path in strings
- Unit: entity routers import/use `HTTPBearer` consistently

### Acceptance
- Generated apps show a clear, consistent security model in OpenAPI and code; cookie mode is guarded/documented.

---

## Epic 3 — Compliance toggles (industry‑aware scaffolds)

### Goals
- Surface actionable compliance notes/toggles per industry with zero external dependencies.

### Deliverables
- `core/config.py`: boolean toggles for HIPAA/PCI/FERPA flags (default false)
- `middleware/logging.py`: expand redaction list when PCI/HIPAA toggles are on (headers like `stripe-signature`, `x-payment-token`)
- Add compliance comments in sensitive modules (security middleware, services) gated by industry in generator

### Tests (TDD)
- Unit: for healthcare/fintech/education blueprints, generated code contains compliance flags/comments in relevant modules

### Acceptance
- Industry selection results in visible compliance scaffolds (flags and comments) in generated code.

---

## Epic 4 — Generated app quality gates (smoke + security checks)

### Goals
- Strengthen each generated app’s default tests to prevent regressions and ensure baseline security/observability.

### Deliverables
- Emit backend tests asserting:
  - Security headers present (X‑Content‑Type‑Options, X‑Frame‑Options, etc.)
  - `/health` and `/metrics` reachable
  - Logging redacts Authorization/cookies
- Add `tools/manage.py` helper with commands: health, create demo user, print status (no external IO)
- CI: keep existing workflow lean; no service bring‑up in CI

### Tests (TDD)
- Unit: generator emits these tests and helper script (string assertions on artifacts)

### Acceptance
- New projects include the tests and they pass locally by default.

---

## Prioritization & Methodology
- Pareto: implement minimal slices advancing deployment, security, compliance, and quality gates.
- TDD: write failing tests for generator emission/wiring first; implement the minimal code; refactor while green.
- Commit discipline: small, conventional messages; keep subject ≤ 72 chars; push after epic completion.

## CI/CD Notes
- Unit workflow uses `pytest` directly; Makefile is not relied upon in CI.
- `aiohttp` included in requirements for provider tests.
- No external services started in CI; tests assert emitted code strings only.


---

# Next Four Epics (Phase N+1): Subagent Orchestration, E2E Demo Data, Deployment DX v2, API Surface Hardening

These epics focus on increasing uninterrupted throughput (plan → delegate → execute), developer speed in generated apps, and baseline API quality without adding heavy dependencies.

## Epic A — Subagent orchestration and longer uninterrupted runs (cursor/CLI friendly)

### Goals
- Emulate Claude “plan → delegate to subagents” workflow inside Cursor/CLI without long blocking loops.
- Provide deterministic, resumable steps that batch operations to reduce context rot.

### Deliverables
- `docs/ORCHESTRATION.md`: How to work in “Plan/Think/Do” cycles using short-lived tasks.
- `tools/dev/agent_runner.py`: Lightweight runner that:
  - Loads a YAML plan (tasks with “tests → edits → verify → commit”).
  - Executes steps idempotently (skips completed markers under `.agent_state/`).
  - Provides a single “next” command to continue after interruptions.
- `plans/` examples: `phase_next.yaml` covering 2–3 tasks as a model (tests-first → minimal edits → commit → push).

### Tests (TDD)
- Unit: parse a tiny YAML plan, produce an execution summary (no external IO). String assertions only.

### Acceptance
- Running `python tools/dev/agent_runner.py --plan plans/phase_next.yaml --dry-run` prints ordered steps.
- Adding `--execute` creates `.agent_state/` markers and logs next actions.

---

## Epic B — E2E demo data & seed flows (Developer ergonomics v2)

### Goals
- Make generated apps usable in one minute with demo data ready.

### Deliverables
- Extend `tools/manage.py` with:
  - `seed_basic_data()`: creates minimal org/user/items (template-only, no external DB in CI).
  - `print_routes()` stub: lists key routes for quick navigation.
- Update README “Getting Started” with a 3-step demo path (env → docker-compose → seed).

### Tests (TDD)
- Unit: emitted `tools/manage.py` contains new functions’ signatures and demo text; README contains “seed” instructions.

### Acceptance
- New projects present a clear, working happy-path: start → seed → explore.

---

## Epic C — Deployment DX v2 (one-liner + status)

### Goals
- Simplify local deployment & status checks for generated apps.

### Deliverables
- Emit `scripts/dev.sh` with `up`, `down`, and `status` subcommands (no external network calls in CI).
- Extend `scripts/smoke.sh` to print detected public URL from `project.json` (if present).
- Day One: add a `--status-only` code path to skip generation/deploy and just print last known info (commented in docs).

### Tests (TDD)
- Unit: emitted shell scripts contain the expected subcommand strings; Day One includes “status-only” string in help text.

### Acceptance
- Developers can run a single script to see up/down/status locally; CI remains unaffected.

---

## Epic D — API surface hardening (pagination + validation docstrings)

### Goals
- Improve baseline API ergonomics with minimal surface changes.

### Deliverables
- Entity list endpoints: ensure `skip`/`limit` are present and documented (already present) and add a simple `max_limit` clamp (e.g., 500).
- Add basic docstrings/comments on validation expectations in auth CRUD handlers.
- README: add a short “API conventions” section (pagination, errors, auth).

### Tests (TDD)
- Unit: emitted entity routers contain max limit clamp string; README contains “API conventions”.

### Acceptance
- Generated APIs present predictable, documented pagination and clear validation notes.

---

## Notes on uninterrupted work (Cursor/CLI)
- Use short-lived batched steps: batch read/search/build/test actions rather than long sessions.
- Keep a lightweight execution plan in YAML and mark steps in `.agent_state/` to resume after context loss.
- Decompose epics → tasks with explicit tests, minimal edits, and verification — then commit & push.
- Prefer deterministic string assertions in unit tests for generator outputs; avoid network and external services.

