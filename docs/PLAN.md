# Delivery Plan – Next Four Epics (Org RBAC/Billing v2, Apply-Plan, Observability v2)

This plan reflects the current repository state and defines the next four epics with concrete tasks, test strategy (TDD), and acceptance criteria. It supersedes earlier items already delivered (RBAC scaffolds, jobs/files/email, deployer stubs, safe-write regeneration, org invitations, CI fixes, metrics wiring).

## Current status (done)
- Security/auth: JWT helpers, reset/verify flows, optional TOTP + cookie mode scaffolds
- RBAC: `backend/app/core/rbac.py`, role on `User`, guards on generated endpoints
- Files/email/jobs: S3 storage service, files API (`/files/upload`, `/files/sign-upload`), SMTP email, RQ worker & jobs API
- Deployers: `tools/deployers/{base,fly,render}.py` and DEPLOY_TARGET wiring in Day One
- Regeneration: safe-write and `plan.json`/`conflicts.json` outputs
- Multi-tenant/billing (phase 1): `Organization`, `tenant_id` on entities, `subscription_status` on `User`, billing service & endpoints, org invitations and org RBAC helper
- Observability (phase 1): Structured logging middleware; richer `/health`; Prometheus metrics emitted and wired (`init_metrics(app)`)
- CI: unit workflow runs pytest directly; `aiohttp` added to requirements to satisfy imports

---

## Epic 1 — Org-level RBAC and invitations (Production-ready)

### Goals
- Complete team onboarding and authorization at the organization level.
- Enforce org roles at API boundaries; simple invitation lifecycle.

### Deliverables
- `backend/app/core/org_rbac.py`: require_org_roles(*roles) (already stubbed) refined to use membership lookup
- `backend/app/models/organization.py`: includes `plan` field (done)
- `backend/app/models/invitation.py`: created (done)
- `backend/app/api/invitations.py`:
  - POST `/` create invitation (owner/admin only)
  - POST `/accept` accepts by code and links user->org
  - GET `/pending` lists pending invites (owner/admin)
- `backend/app/models/membership.py` (optional minimal): `user_id`, `organization_id`, `role`
- Tenancy dependency to auto-filter queries by tenant and set `tenant_id` on create

### Tests (TDD)
- Unit: generator emits invitations/membership/org_rbac artifacts (already added baseline)
- Unit: minimal tests for tenancy dependency string presence and role enforcement markers

### Acceptance
- Generated API exposes create/accept invitations routes; org role checks present in code
- Generated entities use tenancy dependency for list/create/update

---

## Epic 2 — Billing v2 (Stripe webhooks, trials, feature flags)

### Goals
- Reflect real subscription status via webhooks; enable trials and plan-based feature flags.

### Deliverables
- Update `backend/app/services/billing_service.py` with webhook parsing (minimal events):
  - `checkout.session.completed` → set `stripe_customer_id`
  - `customer.subscription.updated/created` → set `subscription_status`, `stripe_subscription_id`
- `backend/app/api/billing.py`:
  - POST `/webhook` (exists) → call service; return 200
  - GET `/plans` returns plan JSON
- Feature flags mapping plans→capabilities in `backend/app/core/billing.py`, and guards (reuse `require_active_subscription`) for selected endpoints
- Trial support: default trial state recognized as `trialing`

### Tests (TDD)
- Unit: generator emits webhook handler stubs and plans endpoint text
- Unit: verify `User` fields (`stripe_customer_id`, `stripe_subscription_id`) are present (done)

### Acceptance
- Generated code contains webhook route and updates status fields (stub logic); `/plans` returns plans; guards recognize `trialing` and `active`.

---

## Epic 3 — Regeneration apply-plan CLI (safe auto-apply)

### Goals
- Provide a safe, semi-automatic way to apply non-conflicting file updates using `plan.json`.

### Deliverables
- `tools/apply_plan.py` CLI:
  - Reads `production_projects/<project>/plan.json`
  - Applies `create` actions; for `conflict` actions, leave `.new` and print summary
  - `--dry-run` (default) prints effect; `--apply` performs writes
- Merge markers added to key generated files to set up future semantic merges (non-breaking, comment markers only)
- Migrations assist: if `alembic` present, print guidance (and optional `--autogenerate` flag stub only; no side effects in CI)

### Tests (TDD)
- Unit: tiny test to instantiate CLI module and ensure it can parse a minimal plan dict (no filesystem writes)

### Acceptance
- `python tools/apply_plan.py --dry-run <project>` prints a concise summary; `--apply` creates files for `create` actions and leaves conflicts untouched.

---

## Epic 4 — Observability v2 and Developer Experience

### Goals
- Improve visibility with metrics and logs, and strengthen CI signals.

### Deliverables
- Metrics: already emitting counters/histograms. Add a couple of labeled counters for error responses (optional)
- Logs: rotate simple file logger in generated app (optional)
- Health: keep richer health payload (done); optionally add simple dependency probes (no external connections in CI)
- CI: ensure unit workflow installs extras needed by tests (aiohttp) (done); add a lint-only job (ruff) later

### Tests (TDD)
- Unit: test that `metrics.py` is emitted and `init_metrics(app)` wired (added)

### Acceptance
- New projects expose `/metrics`; unit workflow passes on main

---

## Prioritization & Methodology
- Pareto: implement only minimal viable scaffolds that directly support team onboarding, billing state, safe regeneration, and visibility.
- TDD: write failing unit tests for generator emission/wiring first; then implement minimal code; refactor while green.
- Commit discipline: small, conventional messages; keep subject ≤ 72 chars; push after epic completion.

## CI/CD Notes
- Unit workflow uses `pytest` directly; Makefile is not relied upon in CI.
- `aiohttp` included in requirements for provider tests.

