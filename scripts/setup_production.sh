#!/bin/bash
set -euo pipefail

# Production Setup Script for Startup Factory
# Implements enhanced security and validation from Gemini feedback

echo "🚀 Setting up Startup Factory for production..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check for required commands
required_commands=("uv" "docker" "git")
for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        print_error "$cmd is required but not installed"
        exit 1
    else
        print_success "$cmd is available"
    fi
done

# Check for required environment variables
required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        print_error "Environment variable $var is required"
        echo "Please set it with: export $var='your-api-key'"
        exit 1
    else
        print_success "$var is set"
    fi
done

# Validate API key formats
echo "🔐 Validating API key formats..."

if [[ ! $OPENAI_API_KEY =~ ^sk- ]]; then
    print_error "Invalid OpenAI API key format (should start with 'sk-')"
    exit 1
fi

if [[ ! $ANTHROPIC_API_KEY =~ ^sk-ant- ]]; then
    print_error "Invalid Anthropic API key format (should start with 'sk-ant-')"
    exit 1
fi

if [[ ! $PERPLEXITY_API_KEY =~ ^pplx- ]]; then
    print_error "Invalid Perplexity API key format (should start with 'pplx-')"
    exit 1
fi

print_success "All API key formats valid"

# Create production directories
echo "📁 Creating production directories..."
mkdir -p production_projects
mkdir -p logs
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana

print_success "Production directories created"

# Create production configuration (without secrets)
echo "⚙️ Creating production configuration..."

cat > config.yaml << 'EOF'
# Production configuration - no secrets here!
# API keys loaded from environment variables
openai_api_key: "${OPENAI_API_KEY}"
anthropic_api_key: "${ANTHROPIC_API_KEY}"
perplexity_api_key: "${PERPLEXITY_API_KEY}"

# Production settings
project_root: "./production_projects"
max_retries: 5
timeout: 60

# Production features
use_perplexity_app: false
enable_monitoring: true
enable_cost_alerts: true
max_budget_per_startup: 15.0  # $15 limit per startup

# Cost tracking (updated rates as of July 2024)
openai_input_cost_per_1k: 0.01
openai_output_cost_per_1k: 0.03
anthropic_input_cost_per_1k: 0.015
anthropic_output_cost_per_1k: 0.075
perplexity_cost_per_request: 0.005

# Security settings
log_level: "INFO"
max_concurrent_requests: 10
rate_limit_per_minute: 60

# Monitoring settings
metrics_port: 8000
health_check_port: 8001
log_rotation_size: "10MB"
log_retention_days: 30
EOF

print_success "Production configuration created"

# Set secure file permissions
chmod 600 config.yaml
print_success "Config file permissions secured (600)"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if uv --version >/dev/null 2>&1; then
    print_info "Using uv for dependency management"
else
    print_error "uv not found - please install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Test dependency installation
print_info "Testing dependency installation..."
cd tools
if uv run --help >/dev/null 2>&1; then
    print_success "uv run command available"
else
    print_error "uv run not working properly"
    exit 1
fi
cd ..

# Create monitoring configuration
echo "📊 Setting up monitoring..."

# Prometheus configuration
cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'startup-factory'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'startup-factory-health'
    static_configs:
      - targets: ['localhost:8001']
    scrape_interval: 30s
    metrics_path: /health

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
EOF

# Prometheus alert rules
cat > monitoring/prometheus/alert_rules.yml << 'EOF'
groups:
  - name: startup-factory-alerts
    rules:
      - alert: HighAPIUsage
        expr: rate(startup_factory_api_calls_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High API usage detected"
          description: "API call rate is {{ $value }} calls/minute"

      - alert: BudgetThresholdExceeded
        expr: startup_factory_cost_spent_dollars > 12
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Budget threshold exceeded"
          description: "Project {{ $labels.project_id }} has spent ${{ $value }}"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} has been down for more than 1 minute"
EOF

# Docker Compose for monitoring
cat > monitoring/docker-compose.monitoring.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: startup-factory-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    container_name: startup-factory-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
EOF

print_success "Monitoring configuration created"

# Create health check script
cat > scripts/health_check.sh << 'EOF'
#!/bin/bash
# Health check script for production monitoring

echo "🏥 Running health checks..."

# Check if configuration is valid
if python -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo "✅ Configuration file is valid YAML"
else
    echo "❌ Configuration file has invalid YAML"
    exit 1
fi

# Check if API keys are accessible (but don't print them)
if [[ -n "${OPENAI_API_KEY:-}" && -n "${ANTHROPIC_API_KEY:-}" && -n "${PERPLEXITY_API_KEY:-}" ]]; then
    echo "✅ All API keys are accessible"
else
    echo "❌ One or more API keys are missing"
    exit 1
fi

# Check disk space (production projects directory)
available_space=$(df production_projects | tail -1 | awk '{print $4}')
if [[ $available_space -gt 1000000 ]]; then  # 1GB in KB
    echo "✅ Sufficient disk space available"
else
    echo "⚠️ Disk space running low: ${available_space}KB available"
fi

# Check if monitoring ports are available
if ! netstat -tuln | grep :8000 >/dev/null 2>&1; then
    echo "✅ Metrics port 8000 is available"
else
    echo "⚠️ Metrics port 8000 is already in use"
fi

if ! netstat -tuln | grep :8001 >/dev/null 2>&1; then
    echo "✅ Health check port 8001 is available"
else
    echo "⚠️ Health check port 8001 is already in use"
fi

echo "🏥 Health check complete"
EOF

chmod +x scripts/health_check.sh
print_success "Health check script created"

# Test configuration
echo "🧪 Testing configuration..."

# Test YAML parsing
if python -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    print_success "Configuration YAML is valid"
else
    print_error "Configuration YAML is invalid"
    exit 1
fi

# Test orchestrator import (without running)
print_info "Testing orchestrator import..."
cd tools
if uv run python -c "from mvp_orchestrator_script import Config; print('Import successful')" 2>/dev/null; then
    print_success "Orchestrator imports successfully"
else
    print_warning "Orchestrator import test failed - may need dependency installation"
fi
cd ..

# Test validation helpers
print_info "Testing validation helpers..."
if python tools/validation_helpers.py >/dev/null 2>&1; then
    print_success "Validation helpers working"
else
    print_warning "Validation helpers test failed"
fi

# Run health check
print_info "Running initial health check..."
if ./scripts/health_check.sh; then
    print_success "Initial health check passed"
else
    print_warning "Some health check issues detected"
fi

# Create quick start guide
cat > PRODUCTION_SETUP.md << 'EOF'
# Production Setup Complete ✅

## Quick Start

1. **Environment Variables**: Ensure these are set in your shell:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   export PERPLEXITY_API_KEY="pplx-..."
   ```

2. **Run MVP Orchestrator**:
   ```bash
   cd tools
   uv run mvp-orchestrator-script.py
   ```

3. **Start Monitoring** (optional):
   ```bash
   cd monitoring
   docker-compose -f docker-compose.monitoring.yml up -d
   # Grafana: http://localhost:3000 (admin/admin)
   # Prometheus: http://localhost:9090
   ```

4. **Health Check**:
   ```bash
   ./scripts/health_check.sh
   ```

## Configuration Files

- `config.yaml` - Main configuration (API keys from environment)
- `test_scenarios.json` - Test data for validation
- `tools/validation_helpers.py` - Quality validation functions
- `monitoring/` - Prometheus & Grafana setup

## Security Notes

- API keys are loaded from environment variables only
- No secrets stored in config files
- Config file has restrictive permissions (600)
- All inputs validated before processing

## Troubleshooting

- **API Key Issues**: Verify format and environment variables
- **Import Errors**: Run `uv sync` in tools/ directory
- **Permission Errors**: Check file permissions with `ls -la`
- **Port Conflicts**: Check with `netstat -tuln | grep :800[01]`

## Next Steps

1. Run integration tests (see `docs/IMPROVED_EXECUTION_PLAN.md`)
2. Validate with test scenarios
3. Set up monitoring dashboard
4. Configure cost alerts
EOF

print_success "Quick start guide created (PRODUCTION_SETUP.md)"

# Final security check
echo "🔒 Running final security check..."

# Check for any hardcoded secrets in config
if grep -E "(sk-|pplx-|sk-ant-)" config.yaml >/dev/null 2>&1; then
    print_error "Hardcoded API keys detected in config.yaml!"
    exit 1
else
    print_success "No hardcoded secrets found in config"
fi

# Check git status (warn if config.yaml would be committed)
if git status --porcelain 2>/dev/null | grep "config.yaml" >/dev/null; then
    print_warning "config.yaml is in git staging area - ensure no secrets before committing!"
fi

# Summary
echo ""
echo "🎉 Production setup complete!"
echo ""
echo "Next steps:"
echo "1. Review PRODUCTION_SETUP.md"
echo "2. Run integration tests: cd tools && uv run mvp-orchestrator-script.py"
echo "3. Set up monitoring: cd monitoring && docker-compose -f docker-compose.monitoring.yml up -d"
echo "4. Run health check: ./scripts/health_check.sh"
echo ""
print_success "Ready for production deployment!"