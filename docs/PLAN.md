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

