#!/bin/bash
# Health check script for production monitoring

echo "🏥 Running Startup Factory health checks..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

exit_code=0

# Check if configuration is valid
echo "🔧 Checking configuration..."
if python -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    print_success "Configuration file is valid YAML"
else
    print_error "Configuration file has invalid YAML"
    exit_code=1
fi

# Check if API keys are accessible (but don't print them)
echo "🔐 Checking API keys..."
required_keys=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
for key in "${required_keys[@]}"; do
    if [[ -n "${!key:-}" ]]; then
        print_success "$key is accessible"
    else
        print_error "$key is missing from environment"
        exit_code=1
    fi
done

# Check API key formats
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    if [[ $OPENAI_API_KEY =~ ^sk- ]]; then
        print_success "OpenAI API key format valid"
    else
        print_error "OpenAI API key format invalid (should start with 'sk-')"
        exit_code=1
    fi
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    if [[ $ANTHROPIC_API_KEY =~ ^sk-ant- ]]; then
        print_success "Anthropic API key format valid"
    else
        print_error "Anthropic API key format invalid (should start with 'sk-ant-')"
        exit_code=1
    fi
fi

if [[ -n "${PERPLEXITY_API_KEY:-}" ]]; then
    if [[ $PERPLEXITY_API_KEY =~ ^pplx- ]]; then
        print_success "Perplexity API key format valid"
    else
        print_error "Perplexity API key format invalid (should start with 'pplx-')"
        exit_code=1
    fi
fi

# Check required directories
echo "📁 Checking directories..."
required_dirs=("production_projects" "logs" "monitoring")
for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        print_success "Directory $dir exists"
    else
        print_error "Directory $dir is missing"
        exit_code=1
    fi
done

# Check disk space (production projects directory)
echo "💾 Checking disk space..."
if [[ -d "production_projects" ]]; then
    available_space=$(df production_projects | tail -1 | awk '{print $4}')
    if [[ $available_space -gt 1000000 ]]; then  # 1GB in KB
        print_success "Sufficient disk space available (${available_space}KB)"
    else
        print_warning "Disk space running low: ${available_space}KB available"
    fi
else
    print_error "Cannot check disk space - production_projects directory missing"
    exit_code=1
fi

# Check if monitoring ports are available
echo "🌐 Checking port availability..."
ports_to_check=("8000:Metrics" "8001:Health Check" "9090:Prometheus" "3000:Grafana")
for port_info in "${ports_to_check[@]}"; do
    IFS=':' read -r port name <<< "$port_info"
    if ! netstat -tuln 2>/dev/null | grep ":$port " >/dev/null; then
        print_success "$name port $port is available"
    else
        print_warning "$name port $port is already in use"
    fi
done

# Check Python dependencies
echo "🐍 Checking Python dependencies..."
cd tools 2>/dev/null || {
    print_error "Cannot access tools directory"
    exit_code=1
}

if command -v uv >/dev/null 2>&1; then
    print_success "uv package manager is available"
    
    # Test if we can import required modules
    if uv run python -c "import yaml, json, pathlib; print('Core modules OK')" 2>/dev/null; then
        print_success "Core Python modules are available"
    else
        print_warning "Some Python modules may be missing"
    fi
else
    print_error "uv package manager not found"
    exit_code=1
fi

cd - >/dev/null

# Check Docker (for monitoring)
echo "🐳 Checking Docker..."
if command -v docker >/dev/null 2>&1; then
    print_success "Docker is installed"
    
    if docker info >/dev/null 2>&1; then
        print_success "Docker daemon is running"
    else
        print_warning "Docker daemon may not be running"
    fi
else
    print_warning "Docker not found (monitoring will not work)"
fi

# Check git repository status
echo "📚 Checking repository status..."
if git status >/dev/null 2>&1; then
    # Check if config.yaml is in git (should not be)
    if git ls-files --error-unmatch config.yaml >/dev/null 2>&1; then
        print_warning "config.yaml is tracked by git - ensure no secrets are committed!"
    else
        print_success "config.yaml is not tracked by git (good for security)"
    fi
    
    # Check for uncommitted changes
    if git diff --quiet && git diff --cached --quiet; then
        print_success "Repository is clean"
    else
        print_warning "Repository has uncommitted changes"
    fi
else
    print_warning "Not in a git repository or git not available"
fi

# Check file permissions
echo "🔒 Checking file permissions..."
if [[ -f "config.yaml" ]]; then
    perms=$(stat -f "%Mp%Lp" config.yaml 2>/dev/null || stat -c "%a" config.yaml 2>/dev/null)
    if [[ "$perms" == "600" ]]; then
        print_success "config.yaml has secure permissions (600)"
    else
        print_warning "config.yaml permissions are $perms (should be 600)"
    fi
else
    print_error "config.yaml not found"
    exit_code=1
fi

# Summary
echo ""
echo "🏥 Health check summary:"
if [[ $exit_code -eq 0 ]]; then
    print_success "All critical checks passed - system is healthy"
else
    print_error "Some critical checks failed - review errors above"
fi

exit $exit_code