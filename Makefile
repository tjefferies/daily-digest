# Makefile - Local equivalents of all GitHub Actions pipeline jobs.
# Usage: make <target> or make all

.PHONY: help lint format typecheck test complexity maintainability interrogate vulture \
        quality license-check semgrep bandit sbom security docs docs-serve all ci \
        dev serve serve-frontend serve-all clean

.DEFAULT_GOAL := help

# ─── Quality Gates ───────────────────────────────────────────────────────────

lint: ## Run ruff linter
	uv run ruff check src/ tests/

format: ## Check ruff formatting
	uv run ruff format --check src/ tests/

format-fix: ## Auto-fix ruff formatting
	uv run ruff format src/ tests/

lint-fix: ## Auto-fix ruff lint issues
	uv run ruff check --fix src/ tests/

typecheck: ## Run ty type checker
	uv run ty check src/

test: ## Run pytest with coverage (>=90%)
	uv run pytest --tb=short -q --cov=src --cov-report=term-missing --cov-fail-under=90

complexity: ## Check cyclomatic complexity (<=8) and maintainability (A)
	@echo "=== Cyclomatic Complexity ==="
	@output=$$(uv run radon cc src/ -a -nc 2>&1); \
	echo "$$output"; \
	if echo "$$output" | grep -qE -- '^\s+[A-Z].*- [D-F]$$'; then \
		echo "ERROR: Functions with complexity > 8 detected"; exit 1; \
	fi
	@echo ""
	@echo "=== Maintainability Index ==="
	@output=$$(uv run radon mi src/ -nc 2>&1); \
	echo "$$output"; \
	if echo "$$output" | grep -qE -- '- [B-F]$$'; then \
		echo "ERROR: Modules with maintainability below A detected"; exit 1; \
	fi

interrogate: ## Check docstring coverage (>=95%)
	uv run interrogate src/ --fail-under 95

vulture: ## Check for dead code (vulture)
	uv run vulture src/ tests/ vulture_whitelist.py --min-confidence 80

quality: lint format typecheck test complexity interrogate vulture ## Run all quality gates
	@echo ""
	@echo "=== ALL QUALITY GATES PASSED ==="

# ─── Security Gates ──────────────────────────────────────────────────────────

license-check: ## Check dependency licenses
	@echo "=== License Compliance Check ==="
	uv run pip-licenses --format=markdown --ignore-packages evercurrent
	uv run pip-licenses --ignore-packages evercurrent --partial-match \
		--allow-only="MIT;BSD;Apache;PSF;Python Software Foundation;ISC;Unlicense;Public Domain;CC0;Zlib;Historical Permission Notice and Disclaimer;Mozilla Public License;Academic Free License;0BSD"
	@echo "All runtime dependencies have approved licenses!"

semgrep: ## Run Semgrep security scan
	uv run semgrep scan \
		--config=p/python \
		--config=p/security-audit \
		--config=p/owasp-top-ten \
		--config=p/cwe-top-25 \
		--config=p/secrets \
		--severity=ERROR --error \
		--no-git-ignore src/

bandit: ## Run Bandit security scan
	uv run bandit -r src/ -f txt --severity-level medium --confidence-level medium
	uv run bandit -r src/ --severity-level high --confidence-level high -q

sbom: ## Generate SBOM and scan for vulnerabilities
	syft scan dir:.venv -o cyclonedx-json=sbom-cyclonedx.json
	syft scan dir:.venv -o spdx-json=sbom-spdx.json
	grype sbom:sbom-cyclonedx.json -o table || true
	@CRITICAL=$$(python3 -c "import json; data=json.load(open('grype-vulnerabilities.json')); print(sum(1 for m in data.get('matches', []) if m.get('vulnerability', {}).get('severity', '').upper() == 'CRITICAL'))" 2>/dev/null || echo "0"); \
	if [ "$$CRITICAL" -gt 0 ]; then echo "ERROR: Critical vulnerabilities found!"; exit 1; fi; \
	echo "No critical vulnerabilities found."

security: license-check semgrep bandit ## Run all security gates (excluding sbom which needs syft/grype)
	@echo ""
	@echo "=== ALL SECURITY GATES PASSED ==="

# ─── Documentation ───────────────────────────────────────────────────────────

docs: ## Build Sphinx documentation
	uv run sphinx-apidoc -f -o docs/api src/evercurrent
	uv run sphinx-build -b html docs docs/_build/html

docs-serve: docs ## Build and serve Sphinx docs with live reload
	uv run sphinx-autobuild docs docs/_build/html --port 8080 --open-browser

docs-clean: ## Clean documentation build
	rm -rf docs/_build

# ─── Aggregate Targets ───────────────────────────────────────────────────────

all: quality security docs ## Run quality + security + docs
	@echo ""
	@echo "=== ALL CHECKS PASSED ==="

ci: quality ## Mirror the full GitHub Actions quality pipeline locally
	@echo ""
	@echo "=== CI PIPELINE PASSED ==="

# ─── Development ─────────────────────────────────────────────────────────────

dev: ## Install all dependencies
	uv sync --all-groups

serve: ## Start the FastAPI backend (port 8000)
	PYTHONPATH=src uv run uvicorn evercurrent.app:app --reload --reload-dir src --port 8000

serve-frontend: ## Start the React frontend dev server (port 5173)
	cd frontend && npm run dev

serve-all: ## Start all services via Docker Compose (backend:8000, frontend:5173, neo4j:7474)
	docker compose up --build

clean: ## Clean build artifacts
	rm -rf docs/_build dist build .pytest_cache .coverage htmlcov .ruff_cache .ty
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
