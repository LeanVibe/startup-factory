# Decision Authority Matrix

**Purpose**: Define what Claude can decide autonomously vs what requires human approval

---

## ✅ AUTONOMOUS DECISIONS (No Approval Needed)

### Code Quality & Structure
- Refactoring existing code for clarity/performance
- Adding error handling and logging
- Breaking large functions into smaller ones
- Adding type hints and documentation
- Improving variable and function names
- Code organization and file structure

### Performance Optimizations  
- Caching implementations
- Database query optimizations
- Memory usage improvements
- Response time optimizations (as long as API contracts maintained)
- Algorithmic improvements

### Testing & Validation
- Adding unit tests
- Adding integration tests  
- Improving test coverage
- Adding performance benchmarks
- Adding health checks

### Dependencies & Tools
- Adding development dependencies < 10MB
- Adding utility libraries for common tasks
- Python packages for data processing, logging, etc.
- Development tools (linting, formatting, etc.)

### Documentation
- Code comments and docstrings
- README updates for existing features
- API documentation generation
- Architecture documentation updates

### Bug Fixes
- Fixing crashes and errors
- Fixing performance issues
- Fixing logical bugs
- Security vulnerability fixes (non-breaking)

---

## ⚠️ REQUIRES APPROVAL (Ask First)

### API & Interface Changes
- Changing public API signatures
- Adding/removing API endpoints
- Changing data schemas
- Breaking changes to existing interfaces
- New external integrations

### Major Architecture Changes
- Adding new core services
- Changing service communication patterns  
- Major database schema changes
- Changing deployment architecture
- Adding new external dependencies > 10MB

### Security & Compliance
- Authentication/authorization changes
- Data privacy implementations
- Compliance framework changes (HIPAA, PCI, etc.)
- Security policy modifications
- Encryption implementations

### Business Logic Changes
- Pricing/cost calculation changes
- User workflow modifications
- Business rule changes
- Feature additions/removals
- UI/UX significant changes

### Infrastructure & Deployment
- Production deployment configuration
- Cloud provider changes
- Infrastructure scaling decisions
- Environment configuration changes
- Monitoring/alerting configuration

---

## 🚨 ESCALATE IMMEDIATELY (Stop and Ask)

### High-Risk Changes
- Anything that could cause data loss
- Changes affecting user billing/payments
- Security-critical modifications
- Regulatory compliance changes
- Production outage risk

### Business Decisions
- Feature prioritization changes
- Resource allocation decisions
- Technical debt vs new feature tradeoffs
- Architecture philosophy changes

### Unknown Territory  
- When unsure about impact scope
- When changes affect multiple services
- When performance impact is unknown
- When rollback complexity is high

---

## 🤖 DECISION PROCESS

### Before Making Any Change:
1. **Assess Impact**: How many components affected?
2. **Check Authority**: Is this in my autonomous scope?
3. **Evaluate Risk**: What could go wrong?
4. **Plan Rollback**: How can I safely undo this?

### For Autonomous Decisions:
1. Document the decision in DECISIONS_LOG.md
2. Implement with proper error handling
3. Add tests for the change
4. Commit with clear description
5. Update relevant documentation

### For Approval Required:
1. Add to BLOCKERS.md with full context
2. Explain the problem and proposed solution
3. List pros/cons and alternatives considered
4. Estimate implementation time and risk
5. Wait for human approval before proceeding

---

## 📊 QUALITY GATES (Always Check)

### Before Any Code Change:
- [ ] Health check passes: `./scripts/health_check.sh`
- [ ] No syntax errors in affected files
- [ ] Core imports still work
- [ ] No obvious breaking changes

### Before Committing:
- [ ] All modified files compile cleanly
- [ ] Basic functionality tests pass
- [ ] No security vulnerabilities introduced
- [ ] Documentation updated if needed
- [ ] PROGRESS_LOG.md updated

### Rollback Triggers:
- Any health check failure
- Import errors in core modules
- Performance regression > 20%
- Test failures in critical paths
- System instability indicators

---

**Use this matrix to maintain development velocity while ensuring quality and safety.**