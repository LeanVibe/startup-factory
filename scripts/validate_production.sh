#!/bin/bash
# Production Validation Script
# Comprehensive validation of production readiness

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

echo "🔍 Startup Factory Production Validation"
echo "========================================"

validation_passed=true

# Test 1: Environment Variables
echo "🔑 Testing environment variables..."
required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        print_error "$var is not set"
        validation_passed=false
    else
        print_success "$var is configured"
    fi
done

# Test 2: System Health
echo "🏥 Running system health check..."
if ./scripts/health_check.sh >/dev/null 2>&1; then
    print_success "System health check passed"
else
    print_error "System health check failed"
    validation_passed=false
fi

# Test 3: Integration Tests
echo "🧪 Running integration tests..."
cd tools
if python test_integration_dry_run.py >/dev/null 2>&1; then
    print_success "Integration tests passed"
else
    print_error "Integration tests failed"
    validation_passed=false
fi

# Test 4: API Integration
echo "🔌 Testing API integration..."
if python test_api_integration.py >/dev/null 2>&1; then
    print_success "API integration tests passed"
else
    print_error "API integration tests failed"
    validation_passed=false
fi

cd ..

# Test 5: Monitoring Services
echo "🎯 Checking monitoring services..."
services=(
    "prometheus:9090"
    "grafana:3000"
    "alertmanager:9093"
)

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if curl -s http://localhost:$port >/dev/null 2>&1; then
        print_success "$name is responding on port $port"
    else
        print_warning "$name is not responding on port $port (may need to start monitoring stack)"
    fi
done

# Test 6: MVP Orchestrator
echo "🤖 Testing MVP orchestrator..."
cd tools
if ./mvp-orchestrator-script.py --help >/dev/null 2>&1; then
    print_success "MVP orchestrator is functional"
else
    print_error "MVP orchestrator has issues"
    validation_passed=false
fi

cd ..

# Test 7: File Permissions
echo "🔒 Checking file permissions..."
if [[ $(stat -f "%Mp%Lp" config.yaml 2>/dev/null || stat -c "%a" config.yaml 2>/dev/null) == "600" ]]; then
    print_success "config.yaml has secure permissions (600)"
else
    print_warning "config.yaml permissions should be 600"
fi

# Test 8: Project Structure
echo "📁 Validating project structure..."
required_dirs=(
    "production_projects"
    "logs"
    "monitoring"
    "scripts"
    "tools"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        print_success "Directory $dir exists"
    else
        print_error "Directory $dir is missing"
        validation_passed=false
    fi
done

# Test 9: Critical Files
echo "📄 Checking critical files..."
critical_files=(
    "config.yaml"
    "tools/mvp-orchestrator-script.py"
    "scripts/health_check.sh"
    "scripts/deploy_production.sh"
    "monitoring/docker-compose.monitoring.yml"
)

for file in "${critical_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "File $file exists"
    else
        print_error "File $file is missing"
        validation_passed=false
    fi
done

# Test 10: Cost Budget Validation
echo "💰 Validating cost budget configuration..."
cd tools
cost_validation=$(python -c "
import yaml
with open('../config.yaml', 'r') as f:
    config = yaml.safe_load(f)

max_budget = config.get('max_budget_per_startup', 0)
if max_budget >= 15.0:
    print('PASS: Budget configured at \$${:.2f}'.format(max_budget))
else:
    print('FAIL: Budget too low at \$${:.2f}'.format(max_budget))
" 2>/dev/null)

if [[ $cost_validation == PASS* ]]; then
    print_success "Budget configuration validated"
else
    print_error "Budget configuration issue: $cost_validation"
    validation_passed=false
fi

cd ..

# Summary
echo ""
echo "🏁 Validation Summary"
echo "===================="

if $validation_passed; then
    print_success "ALL VALIDATIONS PASSED"
    echo ""
    print_info "Startup Factory is ready for production use!"
    echo ""
    echo "Next steps:"
    echo "1. Start monitoring: cd monitoring && docker compose -f docker-compose.monitoring.yml up -d"
    echo "2. Create first MVP: cd tools && ./mvp-orchestrator-script.py"
    echo "3. Monitor costs: http://localhost:3000"
    echo ""
    exit 0
else
    print_error "SOME VALIDATIONS FAILED"
    echo ""
    print_info "Please fix the issues above before using in production."
    echo ""
    exit 1
fi