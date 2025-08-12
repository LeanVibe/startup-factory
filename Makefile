# Startup Factory - Main Makefile
.PHONY: help init dev test clean lint deploy health setup-production validate-production validate-templates validate-templates-ci template-regression-test template-benchmark reindex doc-check

# Default target shows help
help: ## Show this help message
	@echo "Startup Factory - AI-Accelerated MVP Development Platform"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Commands
init: ## Create new startup project (make init STARTUP=project-name)
	@if [ -z "$(STARTUP)" ]; then echo "Usage: make init STARTUP=project-name"; exit 1; fi
	@echo "Creating startup: $(STARTUP)"
	@bash scripts/new_startup.sh $(STARTUP)

dev: ## Start full development environment (Docker Compose)
	@echo "Starting Startup Factory development environment..."
	@docker compose up --build

# Testing Commands
test: ## Run all tests (analytics, production, integration, templates)
	@echo "Running comprehensive test suite..."
	@python -m pytest tests/analytics/ -v --tb=short
	@python -m pytest tests/production/ -v --tb=short
	@python -m pytest tests/templates/ -v --tb=short
	@echo "✅ All tests completed"

test-analytics: ## Run analytics engine tests only  
	@python -m pytest tests/analytics/test_analytics_engine.py -v

test-production: ## Run production deployment tests only
	@python -m pytest tests/production/test_production_deployment.py -v

test-coverage: ## Run tests with coverage report
	@python -m pytest tests/ --cov=tools --cov-report=html --cov-report=term

# Quality Commands
lint: ## Run code quality checks (Python)
	@echo "Running code quality checks..."
	@ruff check tools/ --fix
	@ruff format tools/
	@echo "✅ Code quality checks completed"

clean: ## Clean up temporary files and caches
	@echo "Cleaning temporary files..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Production Commands  
setup-production: ## Setup production environment
	@echo "Setting up production environment..."
	@bash scripts/setup_production.sh

validate-production: ## Validate production readiness
	@echo "Validating production deployment..."
	@bash scripts/validate_production.sh

deploy: ## Deploy to production
	@echo "Deploying Startup Factory..."
	@bash scripts/deploy_production.sh

health: ## Run health checks on all systems
	@echo "Running comprehensive health checks..."
	@bash scripts/health_check.sh

# AI Orchestration Commands
orchestrator: ## Run MVP orchestrator script
	@echo "Starting MVP orchestrator..."
	@uv run tools/mvp_orchestrator_script.py

system-check: ## Quick system validation
	@echo "Running system health check..."
	@python tools/quick_system_check.py

# Monitoring Commands  
monitor: ## Start monitoring dashboard
	@echo "Starting monitoring services..."
	@docker compose -f docker-compose.monitoring.yml up -d

logs: ## View orchestrator logs
	@echo "Viewing recent logs..."
	@tail -f tools/logs/*.log 2>/dev/null || echo "No logs found"

# Docs & Index
reindex: ## Regenerate docs/NAV_INDEX.md and docs/nav_index.json
	@echo "Regenerating repository index..."
	@python3 - << 'PY'
import os, json, time
from pathlib import Path
ROOT=Path('.')
EXCLUDES={'.git','.DS_Store','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.idea','.vscode','node_modules','.next'}
SUMMARIZE_DIRS={'demo_generated_mvps','worktrees'}
SUMMARY_THRESHOLD=200
class N:
    def __init__(self,p,is_dir,d):
        self.p=p; self.is_dir=is_dir; self.d=d; self.n=p.name; self.c=[]; self.fc=0; self.dc=0; self.ec={}; self.s=False
    def to_dict(self):
        x={'name':self.n,'path':str(self.p.relative_to(ROOT)),'type':'dir' if self.is_dir else 'file'}
        if self.is_dir:
            x.update({'file_count':self.fc,'dir_count':self.dc,'ext_counts':dict(sorted(self.ec.items(), key=lambda kv:(-kv[1],kv[0]))),'summary_only':self.s,'children':[ch.to_dict() for ch in self.c] if not self.s else []})
        else:
            x['ext']=self.p.suffix.lower() or '(no-ext)'
        return x
def ex(name): return name in EXCLUDES
def sumdir(n, ents):
    for e in ents:
        if ex(e.name): continue
        if e.is_dir(follow_symlinks=False): n.dc+=1
        else:
            n.fc+=1; ext=Path(e.name).suffix.lower() or '(no-ext)'; n.ec[ext]=n.ec.get(ext,0)+1
    n.s=True
def build(p,d=0):
    is_dir=p.is_dir(); n=N(p,is_dir,d)
    if not is_dir: return n
    summarize_only=(p.name in SUMMARIZE_DIRS and d>=1)
    try: ents=list(os.scandir(p))
    except PermissionError: n.s=True; return n
    if summarize_only: sumdir(n,ents); return n
    items=[e for e in ents if not ex(e.name)]
    if len(items)>SUMMARY_THRESHOLD: sumdir(n,items); return n
    for e in sorted(items, key=lambda de:(not de.is_dir(), de.name.lower())):
        cp=Path(e.path); ch=build(cp,d+1)
        if e.is_dir(follow_symlinks=False): n.dc+=1
        else:
            n.fc+=1; ext=cp.suffix.lower() or '(no-ext)'; n.ec[ext]=n.ec.get(ext,0)+1
        n.c.append(ch)
    return n
root=build(ROOT)
files=dirs=0
def walk(n):
    global files, dirs
    if n.is_dir:
        dirs+=1
        if n.s: files+=n.fc
        for ch in n.c: walk(ch)
    else: files+=1
walk(root)
meta={'repo_path':str(ROOT.resolve()),'generated_at':time.strftime('%Y-%m-%d %H:%M:%S %z'),'total_files_estimated':files,'total_dirs_estimated':dirs}
out_dir=ROOT/'docs'; out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir/'nav_index.json','w',encoding='utf-8') as f: json.dump({'meta':meta,'root':root.to_dict()}, f, indent=2)
md=['# Repository Navigation Index','',f"- Generated: {meta['generated_at']}",f"- Approx. files: {files} | dirs: {dirs}", '', '## Top-level','', '| Name | Type | Files | Dirs | Top extensions | Notes |','|------|------|-------|------|----------------|-------|']
for c in root.c:
    from pathlib import Path as P
    if not c.is_dir: md.append(f"| {c.n} | file | 1 | 0 | {P(c.n).suffix or '(no-ext)'} |  |")
    else:
        exts=', '.join([f"{k}:{v}" for k,v in list(sorted(c.ec.items(), key=lambda kv:(-kv[1],kv[0])))[:4]]) or '—'
        note='summary' if c.s else ''
        md.append(f"| {c.n} | dir | {c.fc} | {c.dc} | {exts} | {note} |")
md+=['','## Tree (depth-limited)','']
MAXD=3
def r(n,d=0):
    if d>MAXD: return
    pref='  '*d+'- '
    if n.p==ROOT:
        for ch in n.c: r(ch,d)
        return
    if n.is_dir:
        note=' (summary)' if n.s else ''
        md.append(f"{pref}`{n.n}`/ — files:{n.fc} dirs:{n.dc}{note}")
        if not n.s:
            for ch in n.c: r(ch,d+1)
    else:
        md.append(f"{pref}`{n.n}`")
with open(out_dir/'NAV_INDEX.md','w',encoding='utf-8') as f: f.write('\n'.join(md)+'\n')
print('Index regenerated at', meta['generated_at'])
PY

doc-check: ## Verify docs index files are present and non-empty
	@test -s docs/NAV_INDEX.md && test -s docs/nav_index.json && echo "Docs index OK"

# CI/CD Commands
ci: ## Run continuous integration pipeline
	@echo "Running CI pipeline..."
	@act -j lint-test

ci-full: ## Run full CI/CD pipeline with all checks
	@echo "Running full CI/CD pipeline..."
	@make test
	@make lint  
	@make system-check
	@make validate-templates-ci
	@echo "✅ Full CI/CD pipeline completed"

# Template Quality Gates Commands
validate-templates: ## Validate all cookiecutter templates
	@echo "Running template validation..."
	@python tools/template_validator_cli.py validate-all --verbose

validate-templates-ci: ## Validate templates for CI/CD (strict mode)
	@echo "Running template validation in CI mode..."
	@python tools/template_validator_cli.py ci --min-score 0.8

template-regression-test: ## Run template regression tests
	@echo "Running template regression tests..."
	@python tools/template_validator_cli.py regression-test --verbose

template-benchmark: ## Benchmark template performance
	@echo "Benchmarking template performance..."
	@python tools/template_validator_cli.py benchmark --template neoforge --iterations 5

validate-template: ## Validate specific template (make validate-template TEMPLATE=neoforge)
	@if [ -z "$(TEMPLATE)" ]; then echo "Usage: make validate-template TEMPLATE=template-name"; exit 1; fi
	@python tools/template_validator_cli.py validate --template $(TEMPLATE) --verbose

list-templates: ## List available templates
	@python tools/template_validator_cli.py list

# Development Shortcuts
quick-test: ## Run fastest subset of tests for development
	@python -m pytest tests/analytics/test_analytics_engine.py::TestAnalyticsDatabase::test_database_initialization -v

template-quick-test: ## Run template tests quickly
	@python -m pytest tests/templates/test_template_quality_gates.py::TestTemplateQualityGates::test_neoforge_template_validation -v
