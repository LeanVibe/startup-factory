# Makefile (top‑level)
init:
	@bash scripts/new_startup.sh $(STARTUP)

dev:
	@docker compose up --build

ci:
	@act -j lint-test
