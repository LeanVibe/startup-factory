# Next Four Epics: Detailed Plan

This document outlines four high‑impact epics with concrete deliverables, task breakdowns, and success criteria. Sequence is optimized to de‑risk the founder experience.

## Epic 1 — Production deployment with real public URLs

- Objective: Deliver stable public URLs (beyond localhost) for every run.
- Deliverables:
  - Deployment options: Local Docker, Cloudflare Tunnel, ngrok (opt‑in), and a future “bring your host” path.
  - Deployer abstraction `DeploymentProvider` with implementations and selection in `tools/day_one_experience.py`.
  - Deployment metadata persisted to `production_projects/<project>/project.json`.
  - Health checks + rollback; status surfaced in `--status`.
- Tasks:
  - Add provider interface and implementations (cloudflare, ngrok, local).
  - Add CLI prompt/flags for deploy target.
  - Implement health verification, retries, rollback.
  - Persist deployment info and show in status.
- Success criteria:
  - Option 1 (local) and Option 2 (tunnel) both yield a valid public URL with 200 `/health` response within 3 minutes.

## Epic 2 — Fully runnable MVPs end‑to‑end (scaffold + smoke)

- Objective: Ensure generated projects boot without manual edits.
- Deliverables:
  - Backend scaffold: `backend/app/main.py`, `backend/app/db/database.py`, `backend/app/core/security.py`, `backend/app/core/config.py`, package `__init__.py` files.
  - Central SQLAlchemy `Base` (shared) and `get_db` dependency.
  - Auth working minimally (register/login, JWT create/verify).
  - Alembic minimal config: `alembic.ini`, `alembic/env.py`, versions dir.
  - Frontend shell: `frontend/index.html`, `frontend/src/main.ts`, Vite config (already present via package.json).
  - Docker Compose compatible with scaffold; `deploy.sh` succeeds.
- Tasks:
  - Refactor model generation to import `Base` from `app.db.database`.
  - Generate backend scaffold artifacts.
  - Generate minimal Alembic scaffolding referencing shared metadata.
  - Generate frontend shell and wire to API base URL via env.
  - Update docs in generator (README/API) to reflect structure.
- Success criteria:
  - Freshly generated project: `docker-compose up -d` → `/health` returns 200; `/docs` loads; `POST /auth/register` + `POST /auth/login` succeed.

## Epic 3 — Unify AI calls via provider manager + health monitoring

- Objective: Consistent reliability, metrics, and fallbacks.
- Deliverables:
  - No direct SDK calls in core tools; all routed through `AIProviderManager`.
  - Provider health visible in `--status` and used for graceful warnings.
  - TaskType‑based model routing; env overrides supported.
- Tasks:
  - Refactor `founder_interview_system`, `business_blueprint_generator`, `smart_code_generator` to use `process_task()`.
  - Integrate `ProviderHealthMonitor` during long workflows.
  - Add status surface in CLI.
- Success criteria:
  - Resilience E2E tests show retry/fallback behavior; provider metrics reported.

## Epic 4 — Analytics and feedback loop

- Objective: Measure funnel and drive improvements.
- Deliverables:
  - Event instrumentation: interview start/end, blueprint generated, code generated, deploy started/succeeded/failed.
  - Session report persisted; CLI summary.
- Tasks:
  - Emit events in `startup_factory.py` and `day_one_experience.py`.
  - Aggregate reports with `tools/analytics_engine.py`.
  - Add `--status` KPIs and `analytics --summary`.
- Success criteria:
  - Event stream per run; weekly summary visible; top failure reasons actionable.

## Execution sequence

1) Epic 2 (scaffold and runnable MVPs)
2) Epic 1 (public URLs)
3) Epic 3 (AI reliability consolidation)
4) Epic 4 (analytics)

## Risks and mitigations

- Alembic and shared Base: models must import shared `Base` to enable migrations. Mitigate by updating generator now.
- Docker availability: keep a no‑Docker “demo build” path for local testing.
- Provider limits: rely on existing manager; refactor later in Epic 3.

## Today’s implementation scope

- Implement Epic 2 core scaffold:
  - Shared SQLAlchemy Base and DB session.
  - Security helpers and JWT.
  - App entrypoint + router wiring.
  - Package `__init__.py` files for imports.
  - Adjust model generation to import shared Base.
  - Minimal Alembic scaffolding (env + versions dir) to unblock `alembic upgrade head`.
  - Minimal frontend shell.
