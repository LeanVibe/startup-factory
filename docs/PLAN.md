# Next Epics Detailed Plan (Security, Jobs/Files/Email, Deployers, Regen)

This document captures the missing details and concrete tasks for the next four epics. It serves as the source of truth for implementation and acceptance.

## Epic 1 — Production‑grade identity, auth, and RBAC

### Goals
- Enforce real JWT verification for access tokens
- Support access/refresh rotation, basic refresh flow
- Add email verification and password reset flows
- Introduce role/permission model (RBAC) and dependency helpers

### Deliverables
- `backend/app/core/rbac.py`: `Role` enum (owner, admin, member), `require_roles` dependency
- Update generated `User` model: `role: Optional[str]` (default `member`), `is_verified: bool`
- Update auth endpoints:
  - `/login` → return access + refresh (already implemented)
  - `/refresh` → issue new access (already implemented)
  - `/request-verify`, `/verify` (implemented)
  - `/request-reset`, `/reset` (implemented)
- Middleware/dependencies enforce JWT verification in `get_current_user` (implemented)
- Optional: token blacklist store + rotation hooks (out of scope for first pass)

### Acceptance
- New projects:
  - Successful register → login → access protected endpoint
  - Verify and reset endpoints work in happy path
  - RBAC helper available and wired for easy use in endpoints

## Epic 2 — Background jobs, file uploads, and email

### Goals
- Async job infrastructure with Redis + RQ
- File upload pipeline with S3-compatible storage
- Email sending abstraction with SMTP default

### Deliverables
- `backend/app/worker/worker.py`: RQ worker entrypoint, example job
- docker-compose: add `worker` service (uses same container / depends on redis)
- `backend/app/services/storage_service.py` (implemented) and `backend/app/api/files.py` (upload endpoint)
- `backend/app/services/email_service.py` with SMTP minimal send
- Extended `.env.template` with S3 + SMTP settings (implemented)

### Acceptance
- New projects:
  - Upload endpoint accepts file (<= size limit) and stores to S3-compatible backend (or noop if not configured)
  - Sample job enqueued and visible in logs via worker
  - Email service stub returns success; replaceable with provider credentials

## Epic 3 — Cloud deployers, domain/TLS automation

### Goals
- Abstract deployers and provide first provider skeletons
- Keep tunnels as fallback

### Deliverables
- `tools/deployers/__init__.py`, `base.py`, `fly.py`, `render.py` (skeletons returning clear TODOs)
- Selection flag in `day_one_experience` (ENV: `DEPLOY_TARGET` = local|tunnel|fly|render)
- Metadata persistence extended with deployer info

### Acceptance
- Running with `DEPLOY_TARGET=tunnel` still works (existing), selecting `fly|render` returns actionable message + generated manifests (future step)

## Epic 4 — Regeneration/diffing and migrations assist

### Goals
- Safe regeneration without clobbering user changes
- Migration assistance stub for model diffs

### Deliverables
- Orchestrator safe-write: if file exists, write `*.new` and collect conflicts list
- Generation summary lists conflicts
- Stub `tools/migrations_helper.py` that explains next steps to create Alembic revisions

### Acceptance
- Re-running generator on existing project does not overwrite files; `.new` files are produced and summarized

## Rollout & QA
- Unit tests remain green
- Add minimal unit to assert presence of new scaffold files (files API, worker entry)
- Manual smoke of generated project

---

## Implementation Notes
- Start with RBAC + files/email/jobs scaffolding in generator
- Add compose worker service and verify references
- Integrate safe-write in orchestrator to protect existing files
- Deployer skeletons for future provider-specific integration
