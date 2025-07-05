# Makefile (top‑level)
init:
\t@bash scripts/new_startup.sh $(STARTUP)

dev:
\t@docker compose up --build

ci:
\t@act -j lint-test
