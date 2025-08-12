# Agent Onboarding Guide (Post-Transformation)

**Purpose**: Enable new contributors and CLI agents to become productive quickly in the founder-focused, conversation-driven system.

## ✅ What This Project Is Now

**Startup Factory** is an AI system that takes a founder from idea to a live MVP in 25 minutes through intelligent conversation. The complex multi-provider, multi-track platform was replaced with a single-command workflow and 6 core AI modules.

Reference: `README.md`, `CLAUDE.md`, `TRANSFORMATION_COMPLETE.md`.

## 🗺️ Start Here

1. Read: `README.md` (overview), `CLAUDE.md` (dev guide)
2. Browse: `docs/NAV_INDEX.md` for a clickable repository map
3. Run locally:
   - `python startup_factory.py` — interactive menu
   - `python startup_factory.py --status` — health check
   - `python startup_factory.py --demo` — demo flow

## 🧠 Core Architecture (Current)

```
startup_factory.py                  # Unified entry point
tools/
  founder_interview_system.py       # 15-min AI conversation
  business_blueprint_generator.py   # Turns interview into blueprint
  smart_code_generator.py           # Generates production code
  streamlined_mvp_orchestrator.py   # <200 lines workflow
  day_one_experience.py             # 25-min idea→live pipeline
production_projects/                # Generated MVPs
```

## 🛠 Dev Tasks You’ll Likely Do

- Improve conversation quality in `tools/founder_interview_system.py`
- Enhance blueprint→code mapping in `tools/business_blueprint_generator.py`
- Add safeguards and quality gates in `tools/streamlined_mvp_orchestrator.py`
- Refine Day One UX in `tools/day_one_experience.py`

Use the following to validate changes:
```bash
python -m py_compile startup_factory.py
python -m py_compile tools/*.py
python startup_factory.py --status
```

## 🔑 Secrets and Providers

- Default and only required AI provider: Anthropic (Claude)
- Set `ANTHROPIC_API_KEY` in your environment (no other keys needed)
- Never commit secrets. Prefer `.env.example` patterns and local env vars

## 📏 Code and Docs Standards

- Follow `CLAUDE.md` for code style, error handling, and UX
- Keep code high-verbosity and readable; prefer clear names
- Update docs when behavior or UX changes
  - `README.md` for user-facing changes
  - `CLAUDE.md` for system/dev guidance
  - `docs/NAV_INDEX.md` is auto-generated; don’t hand-edit

## 🧪 Testing and Validation

- Compile Python modules as smoke tests
- Run any existing tests in `tests/` where relevant
- Manually exercise menu flows via `startup_factory.py`

## 🗃️ Legacy Notes (What’s Gone)

- Multi-provider orchestration (OpenAI/Perplexity) → removed
- Multi-track worktree process (A/B/C/D) → archived
- Heavy template ecosystem → replaced with AI-generated code

If you find outdated docs, prefer the truth in `README.md` and `CLAUDE.md`.

## 🔄 Workflow

- Small, focused edits; keep PRs scoped
- Include brief rationale in commit messages
- Ensure health check passes before submitting

Welcome aboard. Optimize for founder outcomes and a delightful 25-minute journey.