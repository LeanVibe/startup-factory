#\!/bin/bash
# Fast health check for autonomous development sessions
# Usage: ./scripts/health_check.sh

set -e

echo "🏥 Startup Factory Health Check"
echo "==============================="

# Python syntax check (critical)
echo "🐍 Python Syntax Check:"
PYTHON_OK=true
for file in core/*.py startup_factory_v2.py; do
    if [ -f "$file" ]; then
        if \! python -m py_compile "$file" 2>/dev/null; then
            echo "  ❌ Syntax error in $file"
            PYTHON_OK=false
        fi
    fi
done

if [ "$PYTHON_OK" = true ]; then
    echo "  ✅ All Python files compile cleanly"
else
    echo "  ❌ Fix syntax errors before continuing"
    exit 1
fi

# Core imports check (critical)
echo "🔗 Core Module Imports:"
IMPORTS_OK=true

# Test critical imports with proper Python path handling
PYTHONPATH=. python -c "
import sys
sys.path.insert(0, 'core')

try:
    import conversation_service
    import code_generation_service
    import orchestration_service
    import deployment_service
    import multi_tenant_service
    import ai_orchestration_service
    import observability_service
    import integration_service
    print('✅ All core services importable')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || IMPORTS_OK=false

if [ "$IMPORTS_OK" = false ]; then
    exit 1
fi

# Git status
echo "📝 Git Status:"
if [ -z "$(git status --porcelain)" ]; then
    echo "  ✅ Working directory clean"
else
    echo "  ⚠️ Uncommitted changes ($(git status --porcelain | wc -l | tr -d ' ') files)"
fi

# Recent commits
echo "📚 Recent Activity:"
git log --oneline -3 | sed 's/^/  /'

# System resources
echo "💻 System Resources:"
if command -v python >/dev/null 2>&1; then
    echo "  ✅ Python $(python --version 2>&1 | cut -d' ' -f2)"
else
    echo "  ❌ Python not found"
fi

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        echo "  ✅ Docker available"
    else
        echo "  ⚠️ Docker installed but not running"
    fi
else
    echo "  ⚠️ Docker not found (deployment will be limited)"
fi

# Final status
echo "==============================="
if [ "$PYTHON_OK" = true ] && [ "$IMPORTS_OK" = true ]; then
    echo "✅ SYSTEM HEALTHY - Ready for development"
    exit 0
else
    echo "❌ SYSTEM ISSUES DETECTED - Fix before continuing"
    exit 1
fi
EOF < /dev/null