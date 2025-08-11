#\!/bin/bash
# Initialize Claude development session
# Usage: ./scripts/start_claude_session.sh [session_name]

SESSION_NAME="${1:-session_$(date +%Y%m%d_%H%M%S)}"
SESSION_DIR=".claude/sessions/$SESSION_NAME"

echo "🚀 Starting Claude Development Session: $SESSION_NAME"
echo "=================================================="

# Create session directory
mkdir -p "$SESSION_DIR"

# Initialize session metadata
cat > "$SESSION_DIR/README.md" << EOL
# Claude Development Session: $SESSION_NAME

**Started**: $(date)
**Branch**: $(git branch --show-current)
**Commit**: $(git rev-parse --short HEAD)

## Session Goals
[Add your goals for this session]

## Context
[Add important context for autonomous work]
EOL

# Copy current state
echo "📋 Capturing current state..."
cp docs/TODO.md "$SESSION_DIR/initial_todo.md" 2>/dev/null || echo "# No TODO.md found" > "$SESSION_DIR/initial_todo.md"
git status --porcelain > "$SESSION_DIR/initial_git_status.txt"
git log --oneline -10 > "$SESSION_DIR/recent_commits.txt"

# Initialize working memory files  
cat > "$SESSION_DIR/CURRENT_FOCUS.md" << EOL
# Current Focus

**Task**: [What I'm working on right now]
**Priority**: Critical/High/Medium/Low
**Estimated Time**: [30min/1h/2h/4h]
**Success Criteria**: 
- [ ] [Specific measurable outcome]

**Status**: Started $(date)
**Next Action**: [Very specific next step]
EOL

cat > "$SESSION_DIR/PROGRESS_LOG.md" << EOL
# Progress Log

## $(date +"%Y-%m-%d %H:%M")
- 🚀 Session started
- 📋 Initial state captured
- ✅ Ready for autonomous development

EOL

cat > "$SESSION_DIR/NEXT_ACTIONS.md" << EOL
# Next Actions (Prioritized)

## High Priority
- [ ] [Task 1 - clear acceptance criteria]
- [ ] [Task 2 - clear acceptance criteria]

## Medium Priority  
- [ ] [Task 3]
- [ ] [Task 4]

## Low Priority
- [ ] [Task 5]
- [ ] [Task 6]

**Last Updated**: $(date)
EOL

cat > "$SESSION_DIR/DECISIONS_LOG.md" << EOL
# Architecture & Design Decisions

## $(date)
[Record key decisions made during autonomous work]

**Decision Format**:
- **Context**: Why this decision was needed
- **Decision**: What was decided  
- **Rationale**: Why this approach was chosen
- **Consequences**: Expected impact

EOL

cat > "$SESSION_DIR/BLOCKERS.md" << EOL
# Blockers & Questions

[Items that need human input or approval]

## Current Blockers
- None

## Questions for Review
- None

**Last Updated**: $(date)
EOL

# Set environment variable
export CLAUDE_SESSION_DIR="$SESSION_DIR"
echo "export CLAUDE_SESSION_DIR=\"$SESSION_DIR\"" > "$SESSION_DIR/session_env.sh"

# Run health check
echo "🏥 Running health check..."
if ./scripts/health_check.sh; then
    echo ""
    echo "✅ Session initialized successfully\!"
    echo "📂 Session directory: $SESSION_DIR"
    echo "🔧 Set environment: source $SESSION_DIR/session_env.sh"
    echo ""
    echo "📋 Key files for autonomous work:"
    echo "   - $SESSION_DIR/CURRENT_FOCUS.md (what I'm doing now)"
    echo "   - $SESSION_DIR/PROGRESS_LOG.md (track accomplishments)" 
    echo "   - $SESSION_DIR/NEXT_ACTIONS.md (prioritized task list)"
    echo "   - $SESSION_DIR/BLOCKERS.md (items needing human input)"
    echo ""
    echo "🤖 Ready for autonomous development\!"
else
    echo "❌ Health check failed. Fix issues before starting session."
    exit 1
fi
EOF < /dev/null