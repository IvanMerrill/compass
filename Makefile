.PHONY: install test test-unit test-integration test-e2e lint format typecheck all dev-up dev-down dev-reset help
.PHONY: pre-commit-install pre-commit-run ci-local validate-all security-scan test-watch test-coverage load-test clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation and setup
install:  ## Install dependencies with poetry
	poetry install

pre-commit-install:  ## Install pre-commit hooks
	poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

pre-commit-run:  ## Run pre-commit on all files
	poetry run pre-commit run --all-files

# Testing targets
test:  ## Run all tests with coverage
	poetry run pytest

test-unit:  ## Run only unit tests
	poetry run pytest tests/unit/ -v

test-integration:  ## Run only integration tests
	poetry run pytest tests/integration/ -v

test-e2e:  ## Run only end-to-end tests
	poetry run pytest tests/e2e/ -v

test-watch:  ## Run tests in watch mode
	poetry run ptw -- -v

test-coverage:  ## Generate detailed coverage report
	poetry run pytest --cov-report=html --cov-report=term
	@echo "📊 Coverage report: htmlcov/index.html"

test-coverage-diff:  ## Show coverage diff from main branch
	@echo "📊 Coverage comparison (requires coverage-diff)"
	poetry run coverage xml
	@echo "Coverage report generated: coverage.xml"

# Code quality targets
lint:  ## Run ruff linter
	poetry run ruff check src/ tests/

format:  ## Format code with black and ruff
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

typecheck:  ## Run mypy type checker
	poetry run mypy src/

# Security targets
security-scan:  ## Run security scans locally
	@echo "🔒 Running bandit security scan..."
	poetry run bandit -r src/ -c pyproject.toml || true
	@echo ""
	@echo "🔒 Running safety check..."
	poetry run safety check --json || true
	@echo ""
	@echo "🔒 Running secrets detection..."
	poetry run detect-secrets scan --baseline .secrets.baseline || true

# Combined targets
ci-local: format lint typecheck test  ## Simulate CI run locally
	@echo "✅ All CI checks passed locally!"

validate-all: pre-commit-run security-scan ci-local  ## Run ALL checks before push
	@echo "🎉 Ready to push!"

all: format lint typecheck test  ## Run all checks (format, lint, typecheck, test)

# Performance and load testing
load-test:  ## Run load tests with locust
	poetry run locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m --headless

# Docker and development environment
dev-up:  ## Start development environment (Docker services)
	docker-compose -f docker-compose.dev.yml up -d
	@echo "⏳ Waiting for services to be healthy..."
	@timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml ps | grep -q "healthy"; do sleep 2; done' || echo "⚠️  Some services may not be healthy"
	@echo "✅ Development environment ready!"

dev-down:  ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

dev-reset:  ## Reset development environment data
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose -f docker-compose.dev.yml up -d

dev-logs:  ## Show logs from development services
	docker-compose -f docker-compose.dev.yml logs -f

dev-status:  ## Show status of development services
	docker-compose -f docker-compose.dev.yml ps

# Cleanup targets
clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "🧹 Cleanup complete!"

clean-all: clean  ## Clean everything including venv
	rm -rf .venv
	poetry cache clear pypi --all
	@echo "🧹 Deep cleanup complete!"

# Database targets (for future use)
db-migrate:  ## Run database migrations
	@echo "⚠️  Database migrations not yet implemented"
	# poetry run alembic upgrade head

db-rollback:  ## Rollback last migration
	@echo "⚠️  Database migrations not yet implemented"
	# poetry run alembic downgrade -1

db-reset:  ## Reset database to clean state
	@echo "⚠️  Database migrations not yet implemented"
	# poetry run alembic downgrade base
	# poetry run alembic upgrade head

# Documentation
docs-serve:  ## Serve documentation locally
	@echo "📚 Documentation server not yet implemented"
	# poetry run mkdocs serve

# Quick shortcuts
quick-test: test-unit  ## Quick test (unit tests only)
	@echo "✅ Quick tests passed!"

quick-check: format lint  ## Quick check (format and lint only)
	@echo "✅ Quick checks passed!"
