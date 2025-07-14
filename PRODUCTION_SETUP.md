# Startup Factory Production Setup Guide

## Overview

This guide will help you deploy the Startup Factory platform in a production environment. The platform is designed to support up to 10 parallel startup MVPs with comprehensive monitoring, cost tracking, and human-in-the-loop gates.

## Prerequisites

### System Requirements

- **OS**: Linux/macOS (Windows with WSL2)
- **RAM**: Minimum 8GB, Recommended 16GB
- **Storage**: Minimum 50GB free space
- **CPU**: 4+ cores recommended
- **Network**: Stable internet connection for API calls

### Software Dependencies

- **Python**: 3.10 or higher
- **Docker**: Latest stable version
- **Git**: For version control
- **uv**: Package manager (automatic installation)

### API Keys Required

You'll need active API keys from:

1. **OpenAI**: For GPT-4o model access
   - Visit: https://platform.openai.com/api-keys
   - Format: `sk-...`

2. **Anthropic**: For Claude model access
   - Visit: https://console.anthropic.com/
   - Format: `sk-ant-...`

3. **Perplexity**: For research capabilities
   - Visit: https://www.perplexity.ai/settings/api
   - Format: `pplx-...`

## Installation Steps

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url> startup-factory
cd startup-factory

# Set up environment variables
cp .env.production.template .env.production
```

Edit `.env.production` with your actual API keys:

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-actual-openai-key
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key
PERPLEXITY_API_KEY=pplx-your-actual-perplexity-key
```

### 2. Load Environment Variables

```bash
# Option 1: Source the file
source .env.production

# Option 2: Export individually
export OPENAI_API_KEY="sk-your-actual-openai-key"
export ANTHROPIC_API_KEY="sk-ant-your-actual-anthropic-key"
export PERPLEXITY_API_KEY="pplx-your-actual-perplexity-key"
```

### 3. Run Production Deployment

```bash
# Execute the automated deployment script
./scripts/deploy_production.sh
```

The deployment script will:
- ✅ Validate all prerequisites
- ✅ Check API key formats
- ✅ Run comprehensive health checks
- ✅ Execute integration tests
- ✅ Start monitoring infrastructure
- ✅ Configure security settings
- ✅ Set up logging and backups

### 4. Verify Deployment

After successful deployment, verify services:

```bash
# Check system health
./scripts/health_check.sh

# Access monitoring dashboards
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9093  # AlertManager
```

## Usage

### Creating Your First MVP

```bash
# Navigate to tools directory
cd tools

# Run the MVP orchestrator
./mvp-orchestrator-script.py
```

Follow the interactive prompts to:
1. Define your startup niche
2. Conduct market research
3. Analyze founder-market fit
4. Generate MVP specifications
5. Design system architecture
6. Plan implementation

### Monitoring and Management

#### Cost Tracking
- Real-time cost monitoring in Grafana dashboard
- Budget alerts when approaching $15 per startup
- Detailed cost breakdown by AI provider

#### Performance Monitoring
- API response times and success rates
- System resource utilization
- Project completion metrics

#### Health Checks
```bash
# Run comprehensive health check
./scripts/health_check.sh

# Create system backup
./scripts/backup_production.sh
```

## Human-in-the-Loop Gates

The platform includes four critical decision gates:

### Gate 0: Niche Validation
- **Trigger**: Market research completion
- **Decision**: Approve niche selection
- **AI Input**: Perplexity market research

### Gate 1: Problem-Solution Fit
- **Trigger**: Problem identification complete
- **Decision**: Go/no-go on problem pursuit
- **AI Input**: Customer research and solution analysis

### Gate 2: Architecture Review
- **Trigger**: Technical architecture design complete
- **Decision**: Approve implementation approach
- **AI Input**: Security and scalability analysis

### Gate 3: Release Readiness
- **Trigger**: MVP development complete
- **Decision**: Approve for launch
- **AI Input**: Quality and security validation

## Cost Management

### Budget Allocation
- **Maximum per startup**: $15.00
- **Typical workflow cost**: $0.29-$0.50
- **Safety margin**: 97%+ budget remaining

### Cost Optimization
- Prompt engineering for efficiency
- Token usage monitoring
- Automatic cost alerts
- Provider switching based on cost/quality

## Security Considerations

### API Key Management
- ✅ Environment variables only
- ✅ No secrets in version control
- ✅ Secure file permissions (600)
- ✅ Audit logging enabled

### Data Protection
- All data stored locally
- No external data transmission beyond API calls
- Encrypted configuration files
- Regular security audits

### Access Control
- Rate limiting (60 requests/minute)
- Concurrent request limits (10 max)
- Session timeouts
- Audit trail logging

## Troubleshooting

### Common Issues

#### API Key Errors
```bash
# Verify environment variables are loaded
echo $OPENAI_API_KEY | head -c 10

# Check API key formats
./scripts/health_check.sh
```

#### Docker Issues
```bash
# Restart monitoring services
cd monitoring
docker compose -f docker-compose.monitoring.yml restart

# Check container logs
docker compose -f docker-compose.monitoring.yml logs
```

#### Python Dependencies
```bash
# Reinstall dependencies
cd tools
python -m pip install --upgrade pyyaml anthropic openai
```

### Log Locations
- **Application logs**: `logs/application/`
- **Error logs**: `logs/error/`
- **Access logs**: `logs/access/`
- **System logs**: Use `journalctl` on Linux

### Support Channels
1. Check the troubleshooting section in README.md
2. Review system health check output
3. Examine monitoring dashboards for insights
4. Check API provider status pages

## Maintenance

### Daily Tasks
- Monitor cost dashboard
- Review system health
- Check for failed projects

### Weekly Tasks
- Review performance metrics
- Update AI prompts based on results
- Backup important project data

### Monthly Tasks
- Update dependencies
- Review security settings
- Analyze cost optimization opportunities
- Update monitoring dashboards

## Scaling Considerations

### Horizontal Scaling
- Current limit: 10 parallel startups
- Each startup requires ~100MB RAM
- Scale by adding more instances

### Vertical Scaling
- Increase RAM for more concurrent projects
- Faster storage for better I/O performance
- More CPU cores for parallel processing

### Cost Scaling
- Monitor total monthly spend
- Adjust budget limits per startup
- Optimize AI provider selection

## Performance Targets

### Response Times
- API calls: <30 seconds
- Market research: <2 minutes
- MVP generation: <10 minutes
- Architecture design: <5 minutes

### Quality Metrics
- Success rate: >95%
- Human approval rate: >80%
- Cost efficiency: <$1 per MVP on average

### Reliability
- Uptime: >99.9%
- Error rate: <0.1%
- Data loss: 0%

## Production Checklist

### Pre-Launch
- [ ] All API keys configured and tested
- [ ] Monitoring dashboards accessible
- [ ] Health checks passing
- [ ] Backup system configured
- [ ] Security settings verified
- [ ] Cost alerts configured

### Post-Launch
- [ ] First MVP successfully created
- [ ] Monitoring data flowing
- [ ] Cost tracking working
- [ ] Performance within targets
- [ ] Documentation updated
- [ ] Team trained on operations

### Ongoing Operations
- [ ] Daily monitoring routine established
- [ ] Backup verification process
- [ ] Incident response procedures
- [ ] Cost optimization reviews
- [ ] Security audit schedule
- [ ] Performance tuning process

## Success Metrics

Track these KPIs to measure platform success:

### Technical Metrics
- System uptime and availability
- API response times and success rates
- Resource utilization efficiency
- Error rates and recovery times

### Business Metrics
- Time to MVP completion
- Cost per successful MVP
- Human approval rates at gates
- Project completion rates

### Quality Metrics
- MVP quality scores
- User satisfaction ratings
- Market validation success
- Technical debt accumulation

---

## Next Steps

After successful production deployment:

1. **Create your first MVP** using the orchestrator
2. **Set up monitoring alerts** for your specific needs
3. **Customize AI prompts** for your target industries
4. **Establish operational procedures** for your team
5. **Plan for scaling** based on usage patterns

The Startup Factory platform is now ready to accelerate your MVP development process while maintaining quality, cost control, and strategic oversight.

Happy building! 🚀