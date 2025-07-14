#!/bin/bash
# Enhanced health check script with CLI fallback validation
# Comprehensive system health including API and CLI tool availability

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

exit_code=0

echo "🏥 Enhanced Health Check for Startup Factory"
echo "==========================================="

# Check if configuration files exist
echo "🔧 Checking configuration files..."
config_files=("config.yaml" "config.enhanced.yaml")
for config_file in "${config_files[@]}"; do
    if [[ -f "$config_file" ]]; then
        if python -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
            print_success "$config_file is valid YAML"
        else
            print_error "$config_file has invalid YAML"
            exit_code=1
        fi
    else
        if [[ "$config_file" == "config.yaml" ]]; then
            print_error "$config_file not found (required)"
            exit_code=1
        else
            print_warning "$config_file not found (optional for CLI fallbacks)"
        fi
    fi
done

# Check API keys availability
echo "🔐 Checking API key availability..."
api_keys=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
available_apis=0

for key in "${api_keys[@]}"; do
    if [[ -n "${!key:-}" ]]; then
        print_success "$key is available"
        available_apis=$((available_apis + 1))
    else
        print_warning "$key is missing (CLI fallback may be used)"
    fi
done

# Check API key formats for available keys
echo "🔍 Validating API key formats..."
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

# Check CLI fallback tools
echo "🛠️  Checking CLI fallback tools..."
cli_tools=("opencode" "claude" "claude-p" "gemini")
available_clis=0

for tool in "${cli_tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        print_success "$tool CLI is available"
        available_clis=$((available_clis + 1))
        
        # Test basic functionality
        if "$tool" --help >/dev/null 2>&1; then
            print_success "$tool responds to --help"
        else
            print_warning "$tool may have issues (--help failed)"
        fi
    else
        print_warning "$tool CLI not found"
    fi
done

# Evaluate provider coverage
echo "📊 Evaluating provider coverage..."
total_providers=3
coverage_score=$((available_apis + available_clis))
max_coverage=$((total_providers * 2))  # API + CLI for each provider

coverage_percentage=$((coverage_score * 100 / max_coverage))

print_info "Provider Coverage Analysis:"
print_info "  Available APIs: $available_apis/$total_providers"
print_info "  Available CLIs: $available_clis/$total_providers"
print_info "  Coverage Score: $coverage_score/$max_coverage ($coverage_percentage%)"

if [[ $coverage_score -ge $total_providers ]]; then
    print_success "Sufficient provider coverage for full workflow"
elif [[ $coverage_score -ge 2 ]]; then
    print_warning "Limited provider coverage - some workflows may be restricted"
else
    print_error "Insufficient provider coverage - workflow may fail"
    exit_code=1
fi

# Check Python dependencies for enhanced orchestrator
echo "🐍 Checking Python dependencies for enhanced features..."
cd tools 2>/dev/null || {
    print_error "Cannot access tools directory"
    exit_code=1
}

enhanced_deps=("yaml" "asyncio" "subprocess" "tempfile")
missing_deps=()

for dep in "${enhanced_deps[@]}"; do
    if python -c "import $dep" 2>/dev/null; then
        print_success "Python module '$dep' available"
    else
        print_error "Python module '$dep' missing"
        missing_deps+=("$dep")
        exit_code=1
    fi
done

# Test enhanced orchestrator syntax
if [[ -f "enhanced_mvp_orchestrator.py" ]]; then
    if python -m py_compile enhanced_mvp_orchestrator.py 2>/dev/null; then
        print_success "Enhanced MVP orchestrator syntax valid"
    else
        print_error "Enhanced MVP orchestrator has syntax errors"
        exit_code=1
    fi
else
    print_warning "Enhanced MVP orchestrator not found"
fi

cd - >/dev/null

# Check required directories
echo "📁 Checking directory structure..."
required_dirs=("production_projects" "logs" "monitoring" "tools" "scripts")
for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        print_success "Directory $dir exists"
    else
        print_error "Directory $dir is missing"
        exit_code=1
    fi
done

# Check disk space
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

# Check port availability for monitoring
echo "🌐 Checking port availability..."
ports_to_check=("8000:Metrics" "8001:Health Check" "9090:Prometheus" "3000:Grafana" "9093:AlertManager")
for port_info in "${ports_to_check[@]}"; do
    IFS=':' read -r port name <<< "$port_info"
    if ! netstat -tuln 2>/dev/null | grep ":$port " >/dev/null; then
        print_success "$name port $port is available"
    else
        print_warning "$name port $port is already in use"
    fi
done

# Check Docker for monitoring
echo "🐳 Checking Docker for monitoring..."
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
    # Check if sensitive config files are tracked
    sensitive_files=("config.yaml" ".env.production")
    for file in "${sensitive_files[@]}"; do
        if [[ -f "$file" ]] && git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
            print_warning "$file is tracked by git - ensure no secrets are committed!"
        else
            print_success "$file is not tracked by git (good for security)"
        fi
    done
    
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
security_files=("config.yaml" ".env.production")
for file in "${security_files[@]}"; do
    if [[ -f "$file" ]]; then
        perms=$(stat -f "%Mp%Lp" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null)
        if [[ "$perms" == "600" ]]; then
            print_success "$file has secure permissions (600)"
        else
            print_warning "$file permissions are $perms (should be 600)"
        fi
    fi
done

# Test enhanced orchestrator functionality
echo "🤖 Testing enhanced orchestrator functionality..."
cd tools
if [[ -f "enhanced_mvp_orchestrator.py" ]]; then
    # Test provider status check
    if python -c "
from enhanced_mvp_orchestrator import EnhancedAPIManager
try:
    manager = EnhancedAPIManager('../config.yaml')
    print('Enhanced orchestrator loads successfully')
except Exception as e:
    print(f'Enhanced orchestrator error: {e}')
    exit(1)
" 2>/dev/null; then
        print_success "Enhanced orchestrator functionality test passed"
    else
        print_error "Enhanced orchestrator functionality test failed"
        exit_code=1
    fi
else
    print_warning "Enhanced orchestrator not found for testing"
fi

cd - >/dev/null

# Generate recommendation report
echo ""
echo "📋 System Readiness Report"
echo "=========================="

if [[ $exit_code -eq 0 ]]; then
    print_success "All critical health checks passed"
    echo ""
    print_info "System Status: READY FOR PRODUCTION"
    echo ""
    print_info "Recommended workflow:"
    if [[ $available_apis -eq 3 ]]; then
        echo "  • Use standard MVP orchestrator with full API access"
        echo "  • Optimal performance and features available"
    elif [[ $available_apis -gt 0 && $available_clis -gt 0 ]]; then
        echo "  • Use enhanced MVP orchestrator with hybrid API/CLI mode"
        echo "  • Good performance with automatic fallbacks"
    elif [[ $available_clis -ge 2 ]]; then
        echo "  • Use enhanced MVP orchestrator with CLI-only mode"
        echo "  • Basic functionality available without API costs"
    else
        echo "  • Install additional CLI tools for better coverage"
        echo "  • Consider obtaining API keys for optimal experience"
    fi
else
    print_error "Some health checks failed - review issues above"
    echo ""
    print_warning "System Status: NEEDS ATTENTION"
    echo ""
    print_info "Recommended actions:"
    if [[ $coverage_score -lt 2 ]]; then
        echo "  • Install CLI fallback tools: ./scripts/setup_fallbacks.sh"
        echo "  • Obtain at least one API key for basic functionality"
    fi
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo "  • Install missing Python dependencies: ${missing_deps[*]}"
    fi
    if [[ $exit_code -eq 1 ]]; then
        echo "  • Fix critical errors listed above"
        echo "  • Re-run health check after fixes"
    fi
fi

echo ""
echo "💡 Quick commands:"
echo "  • Setup CLI fallbacks: ./scripts/setup_fallbacks.sh"
echo "  • Run enhanced orchestrator: cd tools && python enhanced_mvp_orchestrator.py"
echo "  • View fallback guide: cat CLI_FALLBACK_GUIDE.md"

exit $exit_code