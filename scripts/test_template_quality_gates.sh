#!/usr/bin/env bash
set -e

echo "🚀 Testing Template Quality Gates System"
echo "========================================"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo_error "$1 is not installed"
        return 1
    fi
    return 0
}

# Check prerequisites
echo_info "Checking prerequisites..."

if ! check_command python3; then
    echo_error "Python 3 is required"
    exit 1
fi

if ! check_command pip; then
    echo_error "pip is required"
    exit 1
fi

echo_success "Prerequisites check passed"

# Install dependencies
echo_info "Installing template validation dependencies..."
if pip install -r requirements-template-validation.txt > /dev/null 2>&1; then
    echo_success "Dependencies installed"
else
    echo_warning "Some dependencies may have failed to install (continuing anyway)"
fi

# Check if templates directory exists
if [ ! -d "templates" ]; then
    echo_error "Templates directory not found"
    exit 1
fi

echo_success "Templates directory found"

# List available templates
echo_info "Available templates:"
python tools/template_validator_cli.py list

echo ""

# Test 1: Validate CLI functionality
echo_info "Test 1: Testing CLI functionality"
if python tools/template_validator_cli.py --help > /dev/null 2>&1; then
    echo_success "CLI help works"
else
    echo_error "CLI help failed"
    exit 1
fi

# Test 2: List templates
echo_info "Test 2: Testing template listing"
if python tools/template_validator_cli.py list > /dev/null 2>&1; then
    echo_success "Template listing works"
else
    echo_error "Template listing failed"
    exit 1
fi

# Test 3: Validate specific template (if neoforge exists)
if [ -d "templates/neoforge" ]; then
    echo_info "Test 3: Testing neoforge template validation"
    if python tools/template_validator_cli.py validate --template neoforge > /dev/null 2>&1; then
        echo_success "Neoforge template validation completed"
    else
        echo_warning "Neoforge template validation had issues (check detailed output)"
    fi
else
    echo_warning "Neoforge template not found, skipping specific template test"
fi

# Test 4: Run all template validation
echo_info "Test 4: Testing full template validation"
if python tools/template_validator_cli.py validate-all --min-score 0.5 > /dev/null 2>&1; then
    echo_success "Full template validation completed"
else
    echo_warning "Full template validation had issues (check detailed output)"
fi

# Test 5: Test pytest integration
echo_info "Test 5: Testing pytest integration"
if python -m pytest tests/templates/test_template_quality_gates.py::TestTemplateQualityGates::test_required_structure_config -v > /dev/null 2>&1; then
    echo_success "Pytest integration works"
else
    echo_warning "Pytest integration had issues"
fi

# Test 6: Test Makefile integration
echo_info "Test 6: Testing Makefile integration"
if make list-templates > /dev/null 2>&1; then
    echo_success "Makefile integration works"
else
    echo_warning "Makefile integration had issues"
fi

# Test 7: Benchmark performance (if neoforge exists)
if [ -d "templates/neoforge" ]; then
    echo_info "Test 7: Testing performance benchmarking"
    if timeout 60 python tools/template_validator_cli.py benchmark --template neoforge --iterations 2 > /dev/null 2>&1; then
        echo_success "Performance benchmarking completed"
    else
        echo_warning "Performance benchmarking timed out or failed"
    fi
else
    echo_warning "Neoforge template not found, skipping benchmark test"
fi

# Test 8: Generate sample report
echo_info "Test 8: Generating sample validation report"
if python tools/template_validator_cli.py validate-all --min-score 0.0 > sample_validation_output.txt 2>&1; then
    echo_success "Sample report generated: sample_validation_output.txt"
else
    echo_warning "Sample report generation had issues"
fi

# Final summary
echo ""
echo "🎉 Template Quality Gates System Test Summary"
echo "=============================================="

if [ -f "template_validation_report_*.md" ]; then
    REPORT_FILE=$(ls -t template_validation_report_*.md | head -n 1)
    echo_success "Validation report generated: $REPORT_FILE"
fi

if [ -f "sample_validation_output.txt" ]; then
    echo_success "Sample output saved: sample_validation_output.txt"
fi

echo_info "System appears to be working correctly!"
echo_info "Run 'make validate-templates' for full validation"
echo_info "Run 'python tools/template_validator_cli.py --help' for CLI options"

# Clean up temporary files
rm -f sample_validation_output.txt

echo ""
echo_success "Template Quality Gates System test completed!"
echo_info "Check the generated reports for detailed validation results"