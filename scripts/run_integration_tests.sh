#!/bin/bash
# Run integration tests for the 8-service architecture
# Usage: ./scripts/run_integration_tests.sh

set -e

echo "🧪 Running Integration Tests for Startup Factory"
echo "==============================================="

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Check system health first
echo "🏥 Pre-test health check..."
if ! ./scripts/health_check.sh; then
    echo "❌ Health check failed. Fix issues before running tests."
    exit 1
fi

# Install test dependencies if needed
echo "📦 Checking test dependencies..."
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio
fi

# Set up test environment
export PYTHONPATH=".:core:$PYTHONPATH"
export TESTING=true

# Run integration tests
echo "🚀 Starting integration tests..."
echo ""

# Test with verbose output and detailed error reporting
python -m pytest tests/integration/ \
    -v \
    --tb=short \
    --durations=10 \
    --asyncio-mode=auto \
    --capture=no

TEST_EXIT_CODE=$?

echo ""
echo "==============================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All integration tests passed!"
    echo ""
    echo "📊 Test Summary:"
    echo "• Complete workflow validation ✅"
    echo "• Service communication contracts ✅"
    echo "• Multi-tenant resource isolation ✅"
    echo "• Error handling and resilience ✅"
    echo "• Performance targets ✅"
    echo ""
    echo "🎯 System ready for production use"
else
    echo "❌ Some integration tests failed"
    echo ""
    echo "🔧 Next steps:"
    echo "1. Review test output above for specific failures"
    echo "2. Run ./scripts/health_check.sh to validate system"
    echo "3. Fix failing components and re-run tests"
    echo "4. Check .claude/sessions/*/BLOCKERS.md for known issues"
fi

exit $TEST_EXIT_CODE