# Startup Factory - Main Makefile
.PHONY: help init dev test clean lint deploy health setup-production validate-production validate-templates validate-templates-ci template-regression-test template-benchmark

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
