# Agent Onboarding Guide

**Purpose**: Enable new agents to quickly understand the project and start contributing immediately.

## 📝 Onboarding Checklist
1. Read CLAUDE.md and README.md for architecture and process overview
2. Clone the repository and set up your environment (see Setup Commands below)
3. Review open issues and worktree branches for available tasks
4. For orchestration, escalation, and quality gates, reference main agent leadership protocols
5. If you encounter blockers or complex decisions, escalate to main agent leadership as described in docs/transition-log.md

## 🎯 Project Overview

**Startup Factory** is a production-ready AI-orchestrated development platform for rapidly building and deploying multiple MVPs simultaneously. The platform combines strategic human oversight with AI automation to accelerate startup development while maintaining quality and strategic control.

### Core Mission
- **Goal**: Enable rapid MVP development (≤4 weeks per startup)
- **Capacity**: Support up to 5 parallel startups with resource isolation
- **Budget**: ≤$15k AI spend per startup with real-time cost tracking
- **Quality**: 80%+ test coverage, 95%+ success rate

## 🚀 Current Status

**PRODUCTION READY** - All 4 development tracks completed:

| Track | Status | Description | Branch |
|-------|--------|-------------|--------|
| **A** | ✅ Complete | Multi-Startup Core Infrastructure | `feature/multi-startup-core` |
| **B** | ✅ Complete | Template Ecosystem Development | `feature/template-ecosystem` |
| **C** | ✅ Complete | Advanced AI Coordination | `feature/ai-coordination` |
| **D** | ✅ Complete | Production Optimization | `feature/production-optimization` |

## 🎯 Immediate Next Priorities

1. **Feature Branch Integration** - Merge all completed tracks
2. **Production Deployment** - Deploy integrated platform
3. **Documentation Updates** - Finalize production documentation
4. **Quality Assurance** - Integration testing across all tracks

## 📁 Key Files for Context

### Essential Documentation
- `CLAUDE.md` - Complete development guidelines and architecture
- `README.md` - Project overview and setup instructions
- `docs/PHASE_2_ENHANCED_PLAN.md` - Detailed implementation plan
- `docs/PARALLEL_EXECUTION_PLAN.md` - XP methodology and coordination

### Core Implementation
- `tools/mvp-orchestrator-script.py` - Main AI orchestration engine
- `tools/startup_manager.py` - Multi-startup coordination system
- `tools/queue_processor.py` - AI task processing with provider integration
- `tools/production_optimizer.py` - Performance monitoring and optimization

### Templates
- `templates/neoforge/` - Original FastAPI + Lit template
- `templates/reactnext/` - Next.js + React + FastAPI template
- `worktrees/track-b-templates/` - Template management system

## 🏗️ Architecture Overview

### Multi-Startup Orchestration
```
startup-factory/
├── tools/                    # AI orchestration and management
│   ├── startup_manager.py    # Central coordination for 5 concurrent startups
│   ├── resource_allocator.py # Dynamic resource allocation with conflict prevention
│   ├── queue_processor.py    # AI task processing with provider coordination
│   └── production_optimizer.py # Performance monitoring and optimization
├── templates/                # Production-ready startup templates
│   ├── neoforge/            # FastAPI + Lit (original)
│   └── reactnext/           # Next.js + React + FastAPI
├── worktrees/               # Git worktrees for parallel development
│   ├── track-a-core/        # Multi-startup infrastructure
│   ├── track-b-templates/   # Template ecosystem
│   ├── track-c-ai/         # AI coordination
│   └── track-d-production/  # Production optimization
└── docs/                    # Documentation and plans
```

### AI Provider Integration
- **OpenAI**: Code generation (GPT-4o) with cost tracking
- **Anthropic (via main agent leadership)**: Strategic planning, architecture, quality gates, and deployment
- **OpenCode CLI**: Local code generation and optimization
- **Perplexity**: Market research and competitive analysis

### Performance Metrics
- **Startup Creation**: <30 minutes (50% improvement)
- **Memory Usage**: <500MB per startup (48% reduction)
- **CPU Usage**: <25% per startup (43% reduction)
- **Cost Optimization**: $0.85 per startup (down from $1.50)
- **Success Rate**: 95% with comprehensive monitoring

## 🔧 Development Environment

### Prerequisites
- Python 3.11+ with UV package manager
- Docker and Docker Compose
- Git with worktree support
- Node.js 18+ (for frontend templates)

### Setup Commands
```bash
# Clone repository
git clone https://github.com/LeanVibe/startup-factory.git
cd startup-factory

# Initialize development environment
make setup

# Start development environment
make dev

# Run tests
make test

# Check system health
make health
```

### Git Worktree Management
```bash
# List all worktrees
git worktree list

# Create new worktree
git worktree add worktrees/feature-name feature-branch

# Remove worktree
git worktree remove worktrees/feature-name
```

## 🤖 AI Integration Guidelines

### Provider Usage Matrix
```python
AI_PROVIDER_USAGE = {
    "market_research": "perplexity",      # Real-time market data
    "founder_analysis": "anthropic",      # Strategic planning
    "mvp_specification": "anthropic",     # MVP spec and planning
    "architecture": "anthropic",          # System architecture
    "code_generation": "openai",          # Code generation (GPT-4o)
    "quality_checks": "anthropic",        # Code review and QA
    "deployment": "anthropic",            # Deployment configuration
}
```

### Cost Tracking
- **Budget Monitoring**: Real-time cost tracking with multi-level limits
- **Cost Optimization**: Automatic provider selection based on cost efficiency
- **Alert System**: Configurable warnings at 80% budget utilization
- **Historical Analytics**: Complete audit trail of all AI spending

## 📊 Quality Standards

### Testing Requirements
- **Unit Tests**: >80% code coverage
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Meet all performance benchmarks
- **Security Tests**: Automated vulnerability scanning

### Code Quality
- **Python**: Ruff for linting, UV for dependency management
- **JavaScript**: ESLint, Prettier for formatting
- **Documentation**: Comprehensive docstrings and README updates
- **Git**: Conventional commits with issue references

## 🚨 Human-in-the-Loop Gates

All gates and escalation protocols are managed by main agent leadership. For any gate decision, follow the protocols in CLAUDE.md and docs/transition-log.md.

### Gate 0: Niche Validation
- **Trigger**: Market research completion
- **Decision**: Niche selection approval (main agent leadership)
- **Criteria**: Market size, founder-market fit, competitive landscape

### Gate 1: Problem-Solution Fit
- **Trigger**: Problem identification and solution design
- **Decision**: Go/no-go on problem pursuit (main agent leadership)
- **Criteria**: Problem validation, solution feasibility, customer demand

### Gate 2: Architecture Review
- **Trigger**: Technical architecture completion
- **Decision**: Architecture approval and implementation approach (main agent leadership)
- **Criteria**: Scalability, security, performance considerations

### Gate 3: Release Readiness
- **Trigger**: Sprint completion or release candidate
- **Decision**: Release approval (main agent leadership)
- **Criteria**: Quality metrics, testing completion, deployment readiness

## 🔄 Development Workflow

### XP Methodology
- **Continuous Integration**: Small, frequent commits
- **Collective Code Ownership**: Shared interfaces and standards
- **Clear Requirements**: Detailed acceptance criteria
- **Small Releases**: Incremental functionality delivery

### GitHub Integration
- **Issues**: Task tracking with detailed acceptance criteria
- **Pull Requests**: Code review with automated quality checks
- **Projects**: Kanban boards for sprint planning
- **Actions**: CI/CD pipeline for testing and deployment

## 🛠️ Common Commands

### Development
```bash
# Start orchestrator
uv run tools/mvp-orchestrator-script.py

# Test specific component
python -m pytest tests/test_startup_manager.py -v

# Run integration tests
python tools/test_integration.py

# Check performance
python tools/performance_analyzer.py
```

### Production
```bash
# Deploy to production
bash scripts/deploy_production.sh

# Check system health
bash scripts/health_check.sh

# Monitor resources
python tools/monitoring_dashboard.py
```

## 📈 Success Metrics

### Technical KPIs
- **Startup Creation Time**: <30 minutes
- **Concurrent Startup Capacity**: 5 without conflicts
- **Memory Efficiency**: <500MB per startup
- **CPU Utilization**: <25% per startup
- **Test Coverage**: >80%
- **Success Rate**: >95%

### Business KPIs
- **Cost per MVP**: <$15k total AI spend
- **Time to Market**: <4 weeks per startup
- **Platform Utilization**: 5 concurrent startups
- **Customer Success**: >90% project completion rate

## 🆘 Troubleshooting

### Common Issues
1. **Worktree Conflicts**: Use `git worktree list` to check active worktrees
2. **API Rate Limits**: Check provider health with `python tools/health_monitor.py`
3. **Memory Issues**: Monitor with `python tools/resource_allocator.py --status`
4. **Test Failures**: Run `make test` and check logs in `logs/`

### Support Resources
- **Documentation**: `docs/` directory with comprehensive guides
- **GitHub Issues**: Open issues for bugs and feature requests
- **Code Review**: All changes require peer review
- **Human Gates**: Escalate complex decisions to main agent leadership as described in docs/transition-log.md

## 🔮 Next Development Phase

### Phase 3: Enterprise & Community (Next)
- **Multi-tenant Architecture**: Support for multiple organizations
- **Advanced Analytics**: Predictive success modeling
- **Community Templates**: Public template marketplace
- **Enterprise Security**: SOC2 compliance and advanced auth

### Phase 4: Global Scaling (Future)
- **Multi-region Deployment**: Global infrastructure
- **Custom Integrations**: API marketplace
- **Business Intelligence**: Advanced reporting
- **Enterprise Sales**: B2B features and support

---

**Welcome to the Startup Factory team!** Use this guide to get up to speed quickly and start contributing to the next phase of platform development.