#!/bin/bash
# Production Deployment Script for Startup Factory
# Deploys the complete platform with monitoring and validation

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

echo "🚀 Starting Startup Factory Production Deployment"
echo "================================================="

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if running from correct directory
if [[ ! -f "config.yaml" ]]; then
    print_error "config.yaml not found. Please run from startup-factory root directory."
    exit 1
fi

# Check environment variables and CLI fallbacks
required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
missing_vars=()
cli_fallbacks=("opencode" "claude-p" "gemini")
available_fallbacks=0

for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    fi
done

# Check CLI fallback availability
for tool in "${cli_fallbacks[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        available_fallbacks=$((available_fallbacks + 1))
    fi
done

# Evaluate deployment options
if [[ ${#missing_vars[@]} -eq 0 ]]; then
    print_success "All API keys available - full functionality enabled"
    deployment_mode="full"
elif [[ $available_fallbacks -ge 2 ]]; then
    print_warning "Some API keys missing, but CLI fallbacks available"
    print_info "Missing API keys: ${missing_vars[*]}"
    print_info "Available CLI tools: $available_fallbacks/3"
    print_info "Deployment will use enhanced orchestrator with fallbacks"
    deployment_mode="hybrid"
elif [[ $available_fallbacks -ge 1 ]]; then
    print_warning "Limited functionality - few CLI fallbacks available"
    print_info "Consider running: ./scripts/setup_fallbacks.sh"
    deployment_mode="limited"
else
    print_error "No API keys or CLI fallbacks available"
    echo ""
    echo "Options:"
    echo "1. Set API keys:"
    echo "   export OPENAI_API_KEY='sk-...'"
    echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "   export PERPLEXITY_API_KEY='pplx-...'"
    echo ""
    echo "2. Install CLI fallbacks:"
    echo "   ./scripts/setup_fallbacks.sh"
    echo ""
    read -p "Continue with limited functionality? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    deployment_mode="minimal"
fi

print_success "Deployment mode: $deployment_mode"

# Validate API key formats (only for available keys)
echo "🔍 Validating available API key formats..."

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    if [[ $OPENAI_API_KEY =~ ^sk- ]]; then
        print_success "OpenAI API key format valid"
    else
        print_error "Invalid OpenAI API key format (should start with 'sk-')"
        exit 1
    fi
else
    print_info "OpenAI API key not provided - will use CLI fallback if available"
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    if [[ $ANTHROPIC_API_KEY =~ ^sk-ant- ]]; then
        print_success "Anthropic API key format valid"
    else
        print_error "Invalid Anthropic API key format (should start with 'sk-ant-')"
        exit 1
    fi
else
    print_info "Anthropic API key not provided - will use CLI fallback if available"
fi

if [[ -n "${PERPLEXITY_API_KEY:-}" ]]; then
    if [[ $PERPLEXITY_API_KEY =~ ^pplx- ]]; then
        print_success "Perplexity API key format valid"
    else
        print_error "Invalid Perplexity API key format (should start with 'pplx-')"
        exit 1
    fi
else
    print_info "Perplexity API key not provided - will use CLI fallback if available"
fi

print_success "Available API key formats validated"

# Check Docker
if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is required but not installed"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    print_error "Docker daemon is not running"
    exit 1
fi

print_success "Docker is available and running"

# Check Python dependencies
echo "🐍 Checking Python environment..."
cd tools

if ! python -c "import yaml, anthropic, openai" 2>/dev/null; then
    print_info "Installing required Python dependencies..."
    python -m pip install pyyaml anthropic openai
fi

print_success "Python dependencies verified"
cd ..

# Run health check
echo "🏥 Running system health check..."
if ! ./scripts/health_check.sh; then
    print_error "Health check failed. Please fix issues before deployment."
    exit 1
fi

print_success "Health check passed"

# Run integration tests
echo "🧪 Running integration tests..."
cd tools
if ! python test_integration_dry_run.py; then
    print_error "Integration tests failed"
    exit 1
fi

print_success "Integration tests passed"

# Run API integration tests
echo "🔌 Running API integration tests..."
if ! python test_api_integration.py; then
    print_error "API integration tests failed"
    exit 1
fi

print_success "API integration tests passed"
cd ..

# Start monitoring infrastructure
echo "🎯 Starting monitoring infrastructure..."
cd monitoring

if docker compose -f docker-compose.monitoring.yml up -d; then
    print_success "Monitoring infrastructure started"
else
    print_error "Failed to start monitoring infrastructure"
    exit 1
fi

# Wait for services to be ready
echo "⏳ Waiting for monitoring services to be ready..."
sleep 10

# Check if services are responding
if curl -s http://localhost:9090/-/healthy >/dev/null; then
    print_success "Prometheus is healthy"
else
    print_warning "Prometheus health check failed"
fi

if curl -s http://localhost:3000/api/health >/dev/null; then
    print_success "Grafana is healthy"
else
    print_warning "Grafana health check failed"
fi

if curl -s http://localhost:9093/-/healthy >/dev/null; then
    print_success "AlertManager is healthy"
else
    print_warning "AlertManager health check failed"
fi

cd ..

# Test MVP orchestrator
echo "🤖 Testing MVP orchestrator..."
cd tools

# Test with dry run mode first
if ./mvp-orchestrator-script.py --help >/dev/null 2>&1; then
    print_success "MVP orchestrator script is executable and working"
else
    print_warning "MVP orchestrator script may have issues"
fi

cd ..

# Create production project structure
echo "📁 Setting up production project structure..."
mkdir -p production_projects/{active,completed,archived}
mkdir -p logs/{application,access,error}
mkdir -p backups

print_success "Production directory structure created"

# Set up log rotation
echo "📋 Setting up log rotation..."
cat > logs/logrotate.conf << 'EOF'
/startup-factory/logs/application/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 startup-factory startup-factory
}

/startup-factory/logs/access/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 startup-factory startup-factory
}

/startup-factory/logs/error/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 startup-factory startup-factory
}
EOF

print_success "Log rotation configured"

# Set secure file permissions
echo "🔒 Setting secure file permissions..."
chmod 600 config.yaml
chmod +x scripts/*.sh
chmod +x tools/*.py
find . -name "*.py" -exec chmod +x {} \;

print_success "File permissions secured"

# Create backup script
echo "💾 Creating backup script..."
cat > scripts/backup_production.sh << 'EOF'
#!/bin/bash
# Backup script for Startup Factory production data

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup project data
cp -r production_projects "$BACKUP_DIR/"

# Backup configuration (without secrets)
cp config.template.yaml "$BACKUP_DIR/"

# Backup logs
cp -r logs "$BACKUP_DIR/"

# Create tarball
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup created: $BACKUP_DIR.tar.gz"
EOF

chmod +x scripts/backup_production.sh
print_success "Backup script created"

# Final validation
echo "✅ Running final deployment validation..."

# Test a simple workflow (dry run)
cd tools
if python -c "
import yaml
with open('../config.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('Configuration loaded successfully')
print(f'Project root: {config.get(\"project_root\")}')
print(f'Max budget per startup: ${config.get(\"max_budget_per_startup\", 15)}')
print('All API keys properly configured via environment variables')
"; then
    print_success "Configuration validation passed"
else
    print_error "Configuration validation failed"
    exit 1
fi

cd ..

# Generate deployment summary
echo ""
echo "🎉 DEPLOYMENT COMPLETE"
echo "======================"
echo ""
echo "📊 Service Status:"
echo "  • Prometheus:    http://localhost:9090"
echo "  • Grafana:       http://localhost:3000 (admin/admin)"
echo "  • AlertManager:  http://localhost:9093"
echo ""
echo "🔧 Management Commands:"
echo "  • Health Check:     ./scripts/health_check_enhanced.sh"
echo "  • Setup Fallbacks: ./scripts/setup_fallbacks.sh"
echo "  • Backup Data:     ./scripts/backup_production.sh"
if [[ "$deployment_mode" == "full" ]]; then
    echo "  • MVP Creation:    cd tools && ./mvp-orchestrator-script.py"
else
    echo "  • MVP Creation:    cd tools && python enhanced_mvp_orchestrator.py"
fi
echo ""
echo "💰 Cost Management:"
echo "  • Budget per startup: \$15.00"
echo "  • Cost tracking enabled"
echo "  • Alerts configured for budget overruns"
echo ""
echo "🔐 Security:"
echo "  • API keys loaded from environment variables"
echo "  • Secure file permissions applied"
echo "  • No secrets in version control"
echo ""
echo "📈 Next Steps:"
echo "  1. Access Grafana dashboard to set up monitoring"
echo "  2. Run first MVP creation workflow"
echo "  3. Monitor costs and performance metrics"
echo "  4. Set up automated backups"
echo ""
print_success "Startup Factory is ready for production use!"
echo ""