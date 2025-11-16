.PHONY: install test test-unit test-integration lint format typecheck all dev-up dev-down dev-reset help

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies with poetry
	poetry install

test:  ## Run all tests with coverage
	poetry run pytest

test-unit:  ## Run only unit tests
	poetry run pytest tests/unit/

test-integration:  ## Run only integration tests
	poetry run pytest tests/integration/

test-e2e:  ## Run only end-to-end tests
	poetry run pytest tests/e2e/

lint:  ## Run ruff linter
	poetry run ruff check src/ tests/

format:  ## Format code with black and ruff
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

typecheck:  ## Run mypy type checker
	poetry run mypy src/

all: format lint typecheck test  ## Run all checks (format, lint, typecheck, test)

dev-up:  ## Start development environment (Docker services)
	docker-compose -f docker-compose.dev.yml up -d

dev-down:  ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

dev-reset:  ## Reset development environment data
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose -f docker-compose.dev.yml up -d

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
