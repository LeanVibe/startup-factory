# Startup Factory Setup Guide

This guide will help you set up the Startup Factory AI orchestration platform for launching multiple startups simultaneously.

**Note:** All orchestration, escalation, and gate protocols are managed by main agent leadership. See CLAUDE.md and docs/transition-log.md for details.

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- API keys for AI services (OpenAI, Anthropic, Perplexity, Google)

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd startup-factory
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy configuration templates
cp config.yaml.example config.yaml
cp .env.example .env

# Edit config.yaml with your API keys
nano config.yaml

# Edit .env with environment variables
nano .env
```

### 3. Create Your First Startup

```bash
# Create a new startup
make init STARTUP=s-01

# Navigate to the startup directory
cd s-01

# Start development environment
make dev
```

### 4. Launch AI Orchestrator

```bash
# Return to root directory
cd ..

# Start the AI orchestrator
python tools/mvp-orchestrator-script.py --startup s-01
```

## Detailed Configuration

### API Keys Setup

You need API keys from the following providers:

#### OpenAI (Required)
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add to `config.yaml` under `api_keys.openai_api_key`

#### Anthropic (Required)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Add to `config.yaml` under `api_keys.anthropic_api_key`

#### Perplexity (Required)
1. Go to [Perplexity API](https://www.perplexity.ai/settings/api)
2. Generate an API key
3. Add to `config.yaml` under `api_keys.perplexity_api_key`

#### Google AI (Required)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key
3. Add to `config.yaml` under `api_keys.google_api_key`

### Budget Configuration

Set budget limits to control AI spending:

```yaml
budget:
  per_startup_limit: 15000  # $15k per startup
  per_task_limit: 100       # $100 per task
  auto_shutdown_on_budget_exceeded: true
```

### Human Gates Configuration

Configure approval workflows:

```yaml
human_gates:
  gate_0_niche_validation:
    enabled: true
    required_approvers: 1
    timeout_hours: 48
```

## AI Orchestrator Usage

### Starting a New Startup

```bash
# Create startup directory
make init STARTUP=s-01

# Start AI orchestration
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --phase market-research
```

### Available Phases

1. **market-research**: Market analysis and niche validation
2. **founder-fit**: Founder-market fit assessment
3. **mvp-spec**: MVP specification and planning
4. **development**: Code generation and implementation
5. **deployment**: Production deployment setup

### Interactive Mode

```bash
# Interactive startup creation
python tools/mvp-orchestrator-script.py --interactive

# Resume existing startup
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --resume
```

### Monitoring Progress

```bash
# Check startup status
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --status

# View logs
tail -f logs/orchestrator.log

# Check budget usage
python tools/mvp-orchestrator-script.py \
  --budget-report
```

## Human Gate Workflow

### Gate 0: Niche Validation
- **Trigger**: Market research completion
- **Action**: Review market analysis and approve niche selection
- **Approval**: Required to proceed to problem-solution fit

### Gate 1: Problem-Solution Fit
- **Trigger**: Problem identification complete
- **Action**: Validate problem and proposed solution
- **Approval**: Required to proceed to architecture design

### Gate 2: Architecture Review
- **Trigger**: Technical architecture complete
- **Action**: Review system design and architecture decisions
- **Approval**: Required to proceed to development

### Gate 3: Release Readiness
- **Trigger**: MVP development complete
- **Action**: Review quality metrics and deployment readiness
- **Approval**: Required to proceed to production deployment

## Quality Gates

### Automated Quality Checks

```bash
# Run quality checks
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --quality-check

# Test coverage check
cd s-01/backend
docker compose -f docker-compose.dev.yml run --rm api pytest --cov=app

# Lint check
cd s-01/backend
ruff check .
```

### Quality Thresholds

- **Test Coverage**: ≥80%
- **Build Time**: ≤10 minutes
- **Security Scan**: No high/critical vulnerabilities
- **Performance**: API response time <200ms

## Troubleshooting

### Common Issues

#### API Key Errors
```bash
# Check API key configuration
python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['api_keys'])"

# Test API connectivity
python tools/mvp-orchestrator-script.py --test-apis
```

#### Docker Issues
```bash
# Reset Docker environment
docker compose down -v
docker system prune -f
make dev
```

#### Budget Exceeded
```bash
# Check budget usage
python tools/mvp-orchestrator-script.py --budget-report

# Reset budget (development only)
python tools/mvp-orchestrator-script.py --reset-budget --startup s-01
```

#### Human Gate Timeout
```bash
# Check pending approvals
python tools/mvp-orchestrator-script.py --pending-approvals

# Approve gate manually
python tools/mvp-orchestrator-script.py \
  --approve-gate gate_0 \
  --startup s-01
```

### Logs and Debugging

```bash
# View orchestrator logs
tail -f logs/orchestrator.log

# Debug mode
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --debug

# Verbose logging
VERBOSE_LOGGING=true python tools/mvp-orchestrator-script.py \
  --startup s-01
```

### Getting Help

1. **Documentation**: Check `docs/` directory
2. **Issues**: Report issues in GitHub repository
3. **Debug Info**: Use `--debug` flag for detailed output
4. **Configuration**: Validate `config.yaml` syntax

## Advanced Features

### Parallel Development

```bash
# Run multiple startups in parallel
python tools/mvp-orchestrator-script.py --parallel \
  --startups s-01,s-02,s-03

# Set concurrency limits
python tools/mvp-orchestrator-script.py \
  --max-parallel 3 \
  --startups s-01,s-02,s-03
```

### Custom Templates

```bash
# Create custom template
cp -r templates/neoforge templates/my-template

# Use custom template
python tools/mvp-orchestrator-script.py \
  --template my-template \
  --startup s-01
```

### Integration Setup

#### GitHub Integration
```bash
# Setup GitHub integration
gh auth login
export GITHUB_TOKEN=$(gh auth token)

# Auto-create repositories
python tools/mvp-orchestrator-script.py \
  --startup s-01 \
  --create-github-repo
```

#### Slack Notifications
```bash
# Setup Slack webhook
export SLACK_WEBHOOK_URL="your-webhook-url"

# Test notifications
python tools/mvp-orchestrator-script.py --test-slack
```

## Production Deployment

### Environment Setup

```bash
# Production configuration
cp config.yaml.example config.prod.yaml
nano config.prod.yaml

# Set production environment
export ENVIRONMENT=production
export CONFIG_FILE=config.prod.yaml
```

### Security Considerations

1. **API Key Encryption**: Enable in production
2. **Audit Logging**: Monitor all AI interactions
3. **Rate Limiting**: Prevent API abuse
4. **Budget Monitoring**: Set strict limits

### Monitoring

1. **Metrics**: Monitor AI usage and costs
2. **Alerts**: Set up budget and error alerts
3. **Logs**: Centralized logging for all operations
4. **Health Checks**: Monitor system health

## Next Steps

1. **Create First Startup**: Follow the quick start guide
2. **Configure Human Gates**: Set up approval workflows
3. **Monitor Progress**: Track AI spending and progress
4. **Scale Up**: Launch multiple startups in parallel

For more detailed information, see the individual documentation files in the `docs/` directory.