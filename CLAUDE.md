# CLAUDE.md - Startup Factory Development Guide

This file provides guidance to Claude Code when working with the Startup Factory codebase - an AI-accelerated MVP development platform for rapidly building and deploying multiple startups.

## Project Overview

**Startup Factory** is an AI-orchestrated development platform that enables founders to build multiple MVPs simultaneously using a human-in-the-loop methodology. The platform combines strategic human oversight with AI automation to accelerate startup development while maintaining quality and strategic control.

### Core Mission
- **Goal:** Enable rapid MVP development (≤4 weeks per startup)
- **Capacity:** Support up to 10 parallel startups
- **Budget:** ≤$15k AI spend per startup
- **Quality:** 80%+ test coverage, 70%+ automated merge ratio

## Architecture Overview

### Multi-Startup Monorepo Structure (Current)
```
startup-factory/
├── templates/neoforge/          # Cookiecutter template (FastAPI + LitPWA)
│   └── {{cookiecutter.project_slug}}/  # Template project structure
├── tools/                       # AI orchestration tools
│   ├── mvp-orchestrator-script.py      # Main orchestrator
│   ├── meta-fill-integration.py        # Meta-fill integration
│   ├── perplexity-app-integration.py   # Perplexity integration
│   └── mvp_projects/                   # Generated project data
├── docs/                        # Documentation and plans
│   ├── PLAN.md                  # Launch readiness plan
│   ├── TODO.md                  # Development roadmap
│   └── SETUP.md                 # Setup instructions
├── scripts/                     # Automation scripts
│   └── new_startup.sh           # Startup creation script
├── patches/                     # Template customizations
└── s-01/                        # Example startup (for testing)
```

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

## Build and Development Commands

### Setup
```bash
# Create new startup
make init STARTUP=s-03

# Start development environment
make dev

# Run CI locally
make ci
```

### Backend Development
```bash
# Run all tests
docker compose -f backend/docker-compose.dev.yml run --rm api pytest

# Run specific test
docker compose -f backend/docker-compose.dev.yml run --rm api pytest tests/path/to/test_file.py::test_function_name

# Lint code
ruff check backend/

# Format code
ruff format backend/
```

### Frontend Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm run test

# Run specific test
npm run test -- component-name

# Lint and format
npm run lint
npm run format

# Build for production
npm run build
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

### Debug Commands
```bash
# Check service health
docker compose ps

# View logs
docker compose logs -f <service>

# Run specific test with debug
pytest -v -s tests/path/to/test.py

# Run MVP orchestrator
uv run tools/mvp-orchestrator-script.py

# Test orchestrator components
python tools/test-integration.py
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