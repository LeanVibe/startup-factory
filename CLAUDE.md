# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Startup Factory Development Guide

**Summary:**
Startup Factory orchestration and leadership is now managed by main agent leadership. All escalation protocols, provider assignments, and human-in-the-loop gates reference main agent as the orchestrator. For escalation and contact info, see this file and docs/transition-log.md.

**Technical/Documentation Debt Audit:**
- All contributors should periodically audit for technical and documentation debt, especially before major releases. See TODO.md and PLAN.md for audit checklist.

This file provides guidance to Claude Code when working with the Startup Factory codebase - an AI-accelerated MVP development platform for rapidly building and deploying multiple startups.

**Transition Notice:** As of July 2025, main agent leadership has replaced Claude code as the orchestrator. All escalation protocols, provider assignments, and human-in-the-loop gates now reference main agent as the orchestrator. See the transition log and FAQ for details.

## Project Overview

**Startup Factory** is an AI-orchestrated development platform that enables founders to build multiple MVPs simultaneously using a human-in-the-loop methodology. The platform combines strategic human oversight with AI automation to accelerate startup development while maintaining quality and strategic control.

### Core Mission
- **Goal:** Enable rapid MVP development (≤4 weeks per startup)
- **Capacity:** Support up to 10 parallel startups
- **Budget:** ≤$15k AI spend per startup
- **Quality:** 80%+ test coverage, 70%+ automated merge ratio

## Architecture Overview

### Multi-Startup Monorepo Structure
```
startup-factory/                 # Main repository
├── templates/                   # Startup templates
│   └── neoforge/               # FastAPI + LitPWA template
│       ├── cookiecutter.json   # Template configuration
│       └── {{cookiecutter.project_slug}}/  # Template structure
│           ├── backend/         # FastAPI app (Python 3.12+)
│           │   ├── app/         # Main application code
│           │   ├── tests/       # Backend tests (pytest)
│           │   └── docker-compose.dev.yml
│           └── frontend/        # Lit PWA (ES2021+)
│               ├── src/         # Component library
│               ├── test/        # Frontend tests (Vitest)
│               └── package.json
├── tools/                       # AI orchestration system
│   ├── mvp_orchestrator_script.py      # **MAIN ORCHESTRATOR**
│   ├── meta_fill_integration.py        # Template generation
│   ├── perplexity_app_integration.py   # Market research
│   └── ai_providers.py                # Multi-AI coordination
├── worktrees/                   # Parallel development branches
│   ├── track-a-core/           # Multi-startup infrastructure
│   ├── track-b-templates/      # Template ecosystem
│   ├── track-c-ai-coord/       # AI coordination
│   └── track-d-production/     # Production optimization
├── production_projects/         # Generated startups
├── monitoring/                  # Prometheus + Grafana
└── scripts/                    # Automation utilities
    └── new_startup.sh          # Quick startup creation
```

### Key Components to Understand

#### 1. MVP Orchestrator (`tools/mvp_orchestrator_script.py`)
- **Purpose**: Main AI coordination engine for MVP development
- **Dependencies**: Uses uv for dependency management (auto-installs)
- **Key Features**: Human-in-loop gates, multi-AI provider routing, cost tracking
- **Entry Point**: `uv run tools/mvp_orchestrator_script.py`

#### 2. Template System (`templates/neoforge/`)
- **Architecture**: Cookiecutter-based project generation
- **Stack**: FastAPI (backend) + Lit PWA (frontend) + PostgreSQL
- **Features**: Pre-configured auth, testing, monitoring, deployment
- **Generated Structure**: Complete production-ready startup

#### 3. Worktree Development Pattern
- **Strategy**: Parallel development using `git worktree add`
- **Isolation**: Each agent/track works in separate filesystem
- **Integration**: Shared git object store, coordinated merging

### Technology Stack
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery
- **Frontend:** Lit Web Components, Vite, Vitest, Storybook
- **Infrastructure:** Docker, Docker Compose, Terraform, Nomad
- **AI Orchestration:** Python-based with multi-provider integration
- **Testing:** Pytest (backend), Vitest/Playwright (frontend)
- **Monitoring:** Prometheus, Grafana, Sentry

## AI Agent Orchestration

### Task Distribution Matrix (As Implemented)
```python
# Current implementation in mvp-orchestrator-script.py
AI_PROVIDER_USAGE = {
    "market_research": "perplexity",      # Market research, competitive analysis
    "founder_analysis": "anthropic",      # Strategic planning, complex reasoning  
    "mvp_specification": "anthropic",     # MVP spec and planning
    "architecture": "anthropic",          # System architecture design
    "code_generation": "openai",          # Code generation (GPT-4o)
    "quality_checks": "anthropic",        # Code review and quality
    "deployment": "anthropic",            # Deployment configuration
}

# Future roadmap includes:
# - gemini-cli integration for backend development
# - codex-cli integration for frontend development  
# - qodo integration for test generation
```

### Human-in-the-Loop Gates

#### Gate 0: Niche Validation
- **Trigger:** Market research completion
- **Criteria:** Market size validation, founder-market fit, competitive landscape
- **Human Decision:** Niche selection approval
- **AI Input:** Perplexity market research, Claude analysis synthesis

#### Gate 1: Problem-Solution Fit  
- **Trigger:** Problem identification and solution design
- **Criteria:** Problem validation, solution feasibility, customer demand
- **Human Decision:** Go/no-go on problem pursuit
- **AI Input:** Customer research, solution brainstorming

#### Gate 2: Architecture Review
- **Trigger:** Technical architecture completion
- **Criteria:** Scalability, security, performance considerations
- **Human Decision:** Architecture approval and implementation approach
- **AI Input:** Architecture analysis, security scanning, performance predictions

#### Gate 3: Release Readiness
- **Trigger:** Sprint completion or release candidate
- **Criteria:** Quality metrics, testing completion, deployment readiness
- **Human Decision:** Release approval
- **AI Input:** Testing reports, security scans, performance analysis

## Development Workflow

### Branch Strategy
- **Main Branch:** Protected, fast-forward merges only
- **Feature Branches:** `feat/<area>/<agent>/<issue-id>`
- **Worktree Usage:** Parallel development with `git worktree add ../wt-<area>-<agent>`

### Autonomy Levels
- **L0 - Full Human Control:** Strategic decisions, architecture choices, UX design
- **L1 - Human Approval Required:** Feature implementation, third-party integrations
- **L2 - AI with Monitoring:** CRUD endpoints, documentation updates
- **L3 - Fully Autonomous:** Code formatting, routine maintenance

### Quality Requirements
- **Test Coverage:** Minimum 80%
- **Code Quality:** Ruff (Python), ESLint (JavaScript)
- **Security:** Automated scanning with Bandit, OWASP ZAP
- **Performance:** <2s story generation, <500MB memory usage

## Essential Development Commands

### Initial Setup and Project Creation
```bash
# Create new startup project
make init STARTUP=s-03

# Start full development environment (FastAPI + Lit + monitoring)
make dev

# Run complete CI pipeline locally
make ci
```

### MVP Orchestrator - Core Tool
```bash
# Run the main MVP orchestrator (primary AI coordination tool)
uv run tools/mvp_orchestrator_script.py

# Test orchestrator workflow integration
python tools/test_orchestrator_workflow.py

# Check orchestrator API integration status
python tools/test_api_integration.py
```

### Backend Development (Templates and Generated Projects)
```bash
# Navigate to generated project backend
cd templates/neoforge/{{cookiecutter.project_slug}}/backend/

# Run all backend tests with coverage
docker compose -f docker-compose.dev.yml run --rm api pytest --cov=app --cov-report=html

# Run specific test file
docker compose -f docker-compose.dev.yml run --rm api pytest tests/api/test_users.py -v

# Run single test function
docker compose -f docker-compose.dev.yml run --rm api pytest tests/api/test_auth.py::test_login_valid_user -v

# Code quality checks
ruff check app/
ruff format app/

# Database migrations
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
docker compose -f docker-compose.dev.yml run --rm api alembic revision --autogenerate -m "description"

# Start backend development server with hot reload
docker compose -f docker-compose.dev.yml up api
```

### Frontend Development (Lit PWA)
```bash
# Navigate to frontend directory
cd frontend/

# Install dependencies
npm install

# Start development server with hot reload
npm run dev

# Run all tests
npm run test

# Run specific test component
npm run test -- --grep="ComponentName"

# Run E2E tests with Playwright
npm run test:e2e

# Lint and format
npm run lint
npm run format

# Build for production
npm run build

# Serve production build locally
npm run preview
```

## Code Style and Conventions

### Python (Backend)
- **Style:** PEP8, 88 character line limit
- **Type Hints:** Required for all functions
- **Imports:** Standard library → Third-party → Local
- **Error Handling:** Domain-specific exceptions
- **Documentation:** Comprehensive docstrings

### JavaScript/TypeScript (Frontend)
- **Style:** ES2021+, camelCase naming
- **Components:** Lit Web Components, atomic design pattern
- **Testing:** Vitest with >80% coverage
- **Documentation:** JSDoc comments

### Architecture Patterns
- **Backend:** Clean architecture with dependency injection
- **Frontend:** Atomic design (atoms → molecules → organisms → templates → pages)
- **API:** OpenAPI-first design with contracts/api.yaml
- **Testing:** AAA pattern (Arrange-Act-Assert)

## AI Integration Guidelines

### When to Use Each AI Agent (Current Implementation)
- **Perplexity:** Real-time market research, competitive analysis
- **Anthropic (Claude):** Strategic planning, MVP specs, architecture, quality checks, deployment
- **OpenAI (GPT-4o):** Code generation, implementation tasks
- **Future integrations:**
  - **Gemini:** Multi-modal analysis, backend development
  - **Codex:** Frontend development  
  - **Qodo:** Test generation, code quality assurance

### Budget and Cost Management
- **Per-Task Limits:** 20k tokens, 15 minutes maximum
- **Per-Startup Budget:** $15k total AI spend
- **Cost Tracking:** Automated with detailed reporting
- **Guardrails:** Auto-shutdown on budget/time exceeded

## Testing Strategy

### Backend Testing
- **Unit Tests:** pytest with >80% coverage
- **Integration Tests:** Full API endpoint testing
- **Performance Tests:** Load testing with defined SLAs
- **Security Tests:** Automated vulnerability scanning

### Frontend Testing
- **Unit Tests:** Vitest for component testing
- **Integration Tests:** Playwright for E2E testing
- **Visual Tests:** Storybook visual regression testing
- **Accessibility Tests:** Automated a11y checking

## Deployment and Operations

### Environments
- **Development:** Docker Compose with hot reload
- **Staging:** Production-like environment for testing
- **Production:** Containerized deployment with monitoring

### Monitoring and Observability
- **Metrics:** Prometheus with custom dashboards
- **Logging:** Structured logging with Sentry integration
- **Alerting:** Automated alerts for critical issues
- **Performance:** APM with latency and error tracking

## Security Requirements

### Security Baseline
- **Authentication:** JWT-based with refresh tokens
- **Authorization:** Role-based access control
- **Data Protection:** Encryption at rest and in transit
- **Compliance:** OWASP Top 10, security scanning

### Vulnerability Management
- **Automated Scanning:** Bandit, OWASP ZAP nightly scans
- **Dependency Management:** Dependabot for updates
- **Secrets Management:** AWS Secrets Manager
- **Network Security:** Zero-trust architecture

## Performance Targets

### Backend Performance
- **Response Time:** <200ms for API endpoints
- **Database:** <50ms query response time
- **Memory:** <500MB per service
- **Concurrency:** 1000+ concurrent users

### Frontend Performance
- **Load Time:** <2s initial page load
- **Time to Interactive:** <3s
- **Bundle Size:** <500KB compressed
- **Lighthouse Score:** >90 for all metrics

## Common Patterns and Solutions

### Database Patterns
- **Migrations:** Alembic for schema changes
- **Queries:** SQLAlchemy with query optimization
- **Caching:** Redis for session and application cache
- **Backup:** Automated daily backups

### API Design Patterns
- **REST:** RESTful endpoints with proper HTTP methods
- **Validation:** Pydantic models for request/response
- **Error Handling:** Consistent error response format
- **Pagination:** Cursor-based pagination for large datasets

### Frontend Patterns
- **State Management:** Lightweight state management
- **Routing:** Client-side routing with history API
- **Components:** Reusable Lit Web Components
- **Styling:** CSS custom properties with theming

## Development Workflow Integration

### Git Workflow
- **Commits:** Conventional commits with issue numbers
- **PRs:** Automated quality checks before merge
- **Code Review:** AI-assisted with human approval
- **Deployment:** Automated CI/CD pipeline

### Issue Management
- **Tracking:** GitHub Issues with project boards
- **Priorities:** MoSCoW prioritization
- **Estimation:** Story points with velocity tracking
- **Automation:** AI agent assignment based on task type

## Human Gate Decision Framework

### Decision Criteria
- **Risk Level:** Low/Medium/High impact assessment
- **Business Impact:** Revenue, user experience, security
- **Technical Complexity:** Simple/Complex implementation
- **Strategic Importance:** Core/Supporting functionality

### Escalation Process
- **L0 Decisions:** Always require human approval
- **L1 Decisions:** Human approval with AI recommendation
- **L2 Decisions:** AI execution with human monitoring
- **L3 Decisions:** Fully autonomous execution

## Success Metrics and KPIs

### Development Metrics
- **Velocity:** Story points per sprint
- **Quality:** Defect density, test coverage
- **Efficiency:** Cycle time, lead time
- **AI Utilization:** Cost per feature, automation rate

### Business Metrics
- **Time to Market:** MVP development time
- **Cost Efficiency:** Development cost per feature
- **Success Rate:** MVPs reaching market validation
- **Scalability:** Concurrent startup development capacity

## Troubleshooting Guide

### Common Issues
- **Build Failures:** Check Docker containers, dependency versions
- **Test Failures:** Verify test database state, async handling
- **Performance Issues:** Monitor resource usage, optimize queries
- **AI Agent Issues:** Check API keys, rate limits, token usage

## Common Workflows and Debugging

### Quick Startup Creation Workflow
```bash
# 1. Create new startup (copies template)
make init STARTUP=my-startup

# 2. Navigate to new startup
cd my-startup/

# 3. Start development environment
make dev

# 4. Test the generated project
cd backend/ && docker compose -f docker-compose.dev.yml run --rm api pytest
cd frontend/ && npm test
```

### MVP Orchestrator Workflows
```bash
# Run complete AI-powered MVP development workflow
uv run tools/mvp_orchestrator_script.py

# Test specific orchestrator components
python tools/test_orchestrator_workflow.py
python tools/test_api_integration.py

# Check orchestrator configuration
cat tools/config.yaml  # Main config file
cat tools/config.template.yaml  # Template for setup
```

### Debugging Commands
```bash
# Check all running services
docker compose ps

# View real-time logs for specific service
docker compose logs -f api
docker compose logs -f frontend

# Debug backend issues
cd backend/
docker compose -f docker-compose.dev.yml run --rm api python -c "from app.core.config import settings; print(settings)"

# Debug frontend build issues  
cd frontend/
npm run build -- --debug

# Test database connectivity
cd backend/
docker compose -f docker-compose.dev.yml run --rm api python -c "from app.db.session import engine; print(engine.execute('SELECT 1').scalar())"

# Check template generation
python -c "from cookiecutter.main import cookiecutter; cookiecutter('templates/neoforge/')"

# Validate generated project structure
find . -name "*.py" | head -10  # Check Python files
find . -name "*.js" | head -10   # Check JS files
```

### Branch and Worktree Management
```bash
# List current worktrees
git worktree list

# Create new worktree for parallel development
git worktree add ../wt-feature-name feature/feature-name

# Switch between worktrees
cd ../wt-feature-name

# Remove worktree when done
git worktree remove ../wt-feature-name
```

## Best Practices

### Code Quality
- **Documentation:** Keep README and docs updated
- **Testing:** Write tests before implementation
- **Reviews:** All changes require peer review
- **Refactoring:** Regular code cleanup and optimization

### AI Integration
- **Prompt Engineering:** Clear, specific task descriptions
- **Context Management:** Provide relevant context for AI decisions
- **Validation:** Always validate AI-generated code
- **Learning:** Continuous improvement based on AI performance

### Security
- **Principle of Least Privilege:** Minimal access rights
- **Input Validation:** Sanitize all user inputs
- **Secure Dependencies:** Regular security updates
- **Monitoring:** Continuous security monitoring

## Resource Links

### Documentation
- **API Docs:** `/docs` endpoint for OpenAPI specification
- **Architecture:** `docs/architecture.md` for system design
- **Deployment:** `docs/deployment.md` for production setup
- **Testing:** `docs/testing.md` for testing strategies

### External Resources
- **FastAPI:** https://fastapi.tiangolo.com/
- **Lit:** https://lit.dev/
- **Docker:** https://docs.docker.com/
- **Pytest:** https://docs.pytest.org/

This CLAUDE.md file provides comprehensive guidance for developing within the Startup Factory ecosystem, balancing AI automation with human strategic oversight to achieve rapid, high-quality MVP development.