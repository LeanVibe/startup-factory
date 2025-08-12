You are a senior Cursor agent taking over the Startup Factory repo to complete the next 4 epics. Work incrementally, keep tests green, and commit in small, conventional commits. Do not push. Only run short-lived commands. Use provider manager (Anthropic default). Respect the existing coding style and generator structure.

Context summary:
- Unified CLI in `startup_factory.py` with status/demonstration and interactive menu
- Core generation pipeline in `tools/`:
  - `founder_interview_system.py`: interview flow; now uses AIProviderManager for follow-ups/classification with fallbacks
  - `business_blueprint_generator.py`: generates backend/frontend/deploy docs; now includes:
    - Backend scaffold (FastAPI app, shared SQLAlchemy `Base`, config)
    - Security middleware (headers, request size limit, audit hook) and naive `RateLimitMiddleware`
    - Auth endpoints: register/login/refresh + email verify/reset; `get_current_user` verifies JWT
    - Services: `EmailService`, `StorageService` (S3-compatible)
    - Files API: upload endpoint
    - Dockerfile, docker-compose, Alembic stubs, README, API docs
  - `smart_code_generator.py`: business service/UI codegen via provider manager
  - `day_one_experience.py`: end-to-end; tunnels (cloudflared/ngrok) with health checks; deployment metadata persisted; analytics events per phase
- Provider layer in `tools/ai_providers.py` (Anthropic default)
- Analytics engine exists, events now captured in Day One flow
- Tests: unit suite green; added generator scaffold artifact test

High-level goals (from docs/PLAN.md):
1) Security/RBAC
   - Implement RBAC helper and wire to routes where appropriate
   - Optional token blacklist/rotation (first pass can omit persistence)
2) Jobs/Files/Email
   - RQ worker entrypoint and compose service
   - File upload signed-URL or streaming verified; basic constraints
   - SMTP email send (simple implementation) + provider config; mockable in tests
3) Deployers/DNS/TLS (skeletons)
   - Add deployer skeletons (`tools/deployers/`) and selection env `DEPLOY_TARGET`
   - Generate manifests (stub) and return actionable messages
4) Regeneration/diffing & migrations assist
   - Safe-write (write `*.new` when file exists) in orchestrator step that writes artifacts
   - Collect and print summary of conflicts
   - Add `tools/migrations_helper.py` explaining Alembic steps

What to implement next (ordered):
- RBAC helper and minimal usage
  - Add `backend/app/core/rbac.py` with `Role` enum and `require_roles(*roles)` dependency
  - Update `User` model generation to include `role: Optional[str] = "member"`
  - Demonstrate in one generated entity endpoint (e.g., create/update) guarded with `require_roles("admin","owner")`
- Background worker and compose service
  - Add `backend/app/worker/worker.py` with minimal RQ worker consuming a default queue
  - Update docker-compose generator to include `worker` service depending on `web` and `redis`
  - Add example job enqueue endpoint (e.g., `/jobs/sample`) and a trivial job function under `backend/app/services/jobs.py`
- Email send implementation
  - Implement SMTP send in `EmailService` using env vars; leave noop if not configured; keep async interface
- Safe write generation
  - In orchestrators that materialize files (e.g., `tools/streamlined_mvp_orchestrator.py` and generator’s write loop), if file exists, write `filename.new` and record to a `conflicts` list; print summary at the end
- Deployer skeletons
  - Create `tools/deployers/base.py` with interface, and `tools/deployers/fly.py`, `render.py` returning TODO messages and stub manifests under project path

Constraints/notes:
- Keep unit tests green; if you add tests, scope them to fast checks
- Don’t overblock on real cloud integrations; stubs and clear messages are enough for now
- Avoid long-lived processes; no background servers in CI
- Follow commit message checks (subject <= 72 chars)

Suggested commit breakdown:
1) feat(rbac): add Role/require_roles and guard example endpoint
2) feat(worker): add RQ worker entrypoint and compose service
3) feat(email): implement SMTP send in EmailService with env config
4) feat(generator): safe-write behavior and conflict summary
5) feat(deployers): add deployer skeletons and stub manifests
6) chore(tests): add/adjust unit tests to cover new files minimally

Validation steps after implementation:
- Run `python -m pytest tests/unit -q` (should stay green)
- Optionally generate artifacts via the unit test or a local smoke and ensure new files appear
- Inspect deployer skeletons and safe-write output messages
