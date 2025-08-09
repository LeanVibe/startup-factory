Startup‑Factory Handbook

Fast onboarding guide for AI‑accelerated MVP production with FastAPI + LitPWA (and optional SwiftUI)

**Transition Notice (July 2025):** Main agent leadership has replaced Claude code as the orchestrator. All escalation protocols, provider assignments, and human-in-the-loop gates now reference main agent as the orchestrator. See the transition log and FAQ for details.

⸻

0. Purpose & Audience

This single document explains everything a new developer needs to contribute productively from day 1 to a portfolio of up to 10 parallel MVPs. It merges process, architecture, conventions, and tooling drawn from the founder’s agent‑first methodology and boilerplate projects.  ￼

⸻

1. High‑Level Flow (30‑Second View)

Idea → Research → Validation → MVP Spec → Code → Test → Deploy → Iterate
            ▲            │             │
            │            ▼             ▼
        AI research   Human Gates   Production

Phase	Lead AI Tools	Key Human Gate	Output Artifact
Market/Problem research	Perplexity	G0 – Niche validation	Market & competitor reports
Solution & MVP design	Main agent leadership (Anthropic, OpenAI)	G1 – Problem‑solution fit	MVP spec + architecture
Build & test	Main agent leadership (OpenAI, Gemini, Codex)	G2 – Feature completion	Running code + tests
Release & learn	Main agent orchestrator + CI/CD bots	G3 – Release readiness	Production deploy & metrics

(The autonomy model behind these gates is detailed in §7.)  ￼

⸻

2. Repository & Branch / Worktree Conventions

startup-factory/
├── templates/                # Cookiecutter copy of github.com/neoforge-dev/starter
├── s‑01/ … s‑10/             # One directory per startup
│   ├── backend/              # FastAPI code
│   ├── frontend/             # LitPWA code
│   ├── ios/                  # Optional SwiftUI package
│   ├── contracts/api.yaml    # Single OpenAPI source‑of‑truth
│   ├── docs/                 # Auto‑generated research & PRD markdown
│   └── tests/
└── tools/
    ├── mvp‑orchestrator.py   # Task router (see §4)
    └── starter_ai_recipes/   # Scaffold helpers (see §3)

	•	Default branch main (protected, fast‑forward merges only).
	•	Agent branches feat/<area>/<agent>/<issue‑id> (e.g., feat/backend/main-agent/102).
	•	Parallel development via git worktree add ../wt‑<area>-<agent> so each LLM container has an isolated file system but shares the repo object store.  ￼

⸻

3. Boilerplate & Code Generation Shortcuts

3.1 Living Template

templates/ is a read‑only mirror of neoforge‑dev/starter. A nightly GitHub Action watches upstream commits and issues a PR with diffs; local overrides live in /patches/*.patch.

3.2 Cookiecutter Hooks

Running

cookiecutter templates/neoforge \
    --config-file starter.yaml   # filled automatically by the orchestrator

will pre‑configure DB type, auth, and feature flags read from each startup’s docs/mvp.yaml.

3.3 starter_ai_recipes Helpers

from starter_ai_recipes import fastapi_crud_route, lit_pwa_view, swiftui_feature

LLM agents call these to drop in idiomatic scaffolds with tests, avoiding token‑hungry boilerplate.  ￼

⸻

4. AI Agent Orchestrator

The mvp‑orchestrator.py script polls /issues/*.yaml and assigns tasks:

AI_PROVIDER_USAGE = {
    "market_research": "perplexity",
    "founder_analysis": "anthropic",
    "mvp_specification": "anthropic",
    "architecture": "anthropic",
    "code_generation": "openai",
    "quality_checks": "anthropic",
    "deployment": "anthropic",
}
# Future roadmap includes:
# - gemini-cli integration for backend development
# - codex-cli integration for frontend development
# - qodo integration for test generation

Workflow:
	1.	Reads context (docs/ + last diff), spins the proper agent Docker image as directed by the main agent orchestrator.
	2.	Creates/updates a worktree branch.
	3.	Opens a draft PR tagged ai-generated.
	4.	Adds cost/time metadata; shuts down if >20 k tokens or >15 min.

(Budget guardrails—see §8.)  ￼

⸻

5. Contracts‑First Development
	1.	Author contracts/api.yaml (OpenAPI 3.1).
	2.	CI step datamodel-code-generator → Pydantic models.
	3.	openapi-generator-cli →
	•	TypeScript types + Lit fetch mixins
	•	Swift5‑Combine client for iOS (optional)

This guarantees backend/FE parity and slashes integration bugs.

⸻

6. CI/CD Pipeline (GitHub Actions)

Job	Purpose	When
lint‑test	ruff, mypy, pytest, playwright	Every push / PR
doc‑check	Verify required files exist & hash stamp fresh	PR
build‑cache	Turborepo build caching for JS & wasm assets	PR
deploy‑preview	Terraform apply with stack.preview.tfvars (LiteFS + Cloudflare R2)	On label preview
release	Tag → Docker build → prod Terraform	Merge to main

Secrets & AWS keys are stored in OIDC‑backed actions‑role with least privilege.

⸻

7. Human Gates & Autonomy Levels

Level	Who Decides	Examples
L0 – Full human	Founder / Tech Lead	Pivot, funding, UX paradigm
L1 – Human approval	Reviewer via PR	DB schema change, new dependency
L2 – AI with monitoring	CI + dashboards	CRUD endpoints, docs updates
L3 – Fully AI	Orchestrator	Code formatting, dependency bumps

Gate matrix (G0…G3) aligns to Levels: G0 & G1 at L0, G2 at L1, G3 at L1. Lower‑risk tasks flow at L2–L3.

⸻

8. Budgets, Metrics & Guardrails

KPI	Target
Doc cycle time	≤ 48 h
Test coverage	≥ 80 %
Automated merge ratio	≥ 70 %
MVP lead time	≤ 4 wks
LLM spend per startup	≤ $15 k

The orchestrator’s decorator enforces per‑task token/runtime ceilings and flags over‑budget PRs.  ￼

⸻

9. Local Dev Setup

# Prereqs
asdf install python 3.12.3
asdf install nodejs 20
brew install act # run CI jobs locally
git clone git@github.com:<org>/startup-factory && cd startup-factory

# Create a new startup
make init STARTUP=s-03

# Run full stack
make dev          # FastAPI + Lit dev-server (HMR) + Hotrun endpoint
make ios          # (optional) builds SwiftUI playground package

Environment variables are loaded from .envrc (direnv).

⸻

10. SwiftUI Track (Optional)

When a project demands a native iOS front end:
	•	Build as a Swift Package MVP (playground) to bypass App Store review during validation.
	•	Use openapi-generator -g swift5-combine -i contracts/api.yaml for the networking layer.
	•	Follow the architecture diagram template in docs/ios-arch.md.  ￼

⸻

11. Reliability & Security Baseline
	•	Prometheus + Grafana dashboards for latency, error rate, LLM cost.
	•	Sentry integrated with both FastAPI and Lit front end.
	•	Bandit, OWASP ZAP, and Dependabot run nightly.
	•	Zero‑trust IaC: Security groups, database credentials from AWS Secrets Manager.  ￼

⸻

12. Glossary

Term	Meaning
Agent branch	Git branch owned by a single AI assistant
Worktree	Separate checkout sharing .git/objects; prevents merge chaos
Gates (G0…G3)	Mandatory human sign‑offs at key risk points
Starter	FastAPI + LitPWA boilerplate from neoforge-dev/starter
Hotrun	Dev command opening a temporary HMR preview for UI sketches
Orchestrator	Python script assigning tasks to AI agents


⸻

13. First Tasks for the Onboarded Developer
	1.	Install toolchain per §9.
	2.	Pick an open issue labeled needs‑human‑review in s‑01.
	3.	Check out the corresponding worktree (git worktree list).
	4.	Run make dev, verify tests pass, push fixes.
	5.	Request review from the Tech Lead; merge upon G2 approval.

Welcome aboard—ship fast, learn faster! 🚀
