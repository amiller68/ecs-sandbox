.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

PROJECT_ROOT := $(shell cd ../.. && pwd)

.PHONY: setup
setup: ## Start Redis container for background jobs
	@$(PROJECT_ROOT)/bin/redis.sh up
	@mkdir -p $(PROJECT_ROOT)/data

.PHONY: teardown
teardown: ## Stop Redis container
	@$(PROJECT_ROOT)/bin/redis.sh down

.PHONY: dev
dev: ## Run development server
	@./bin/dev.sh

.PHONY: worker
worker: ## Run TaskIQ worker
	@./bin/worker.sh

.PHONY: scheduler
scheduler: ## Run TaskIQ scheduler
	@./bin/scheduler.sh

.PHONY: test
test: ## Run tests
	@uv run pytest || test $$? -eq 5

.PHONY: lint
lint: ## Run linting
	@uv run ruff check src/ tests/

.PHONY: fmt
fmt: ## Format code
	@uv run black src/ tests/

.PHONY: fmt-check
fmt-check: ## Check formatting
	@uv run black --check src/ tests/

.PHONY: types
types: ## Run type checking
	@uv run ty check src/ tests/

.PHONY: check
check: fmt-check lint types test ## Run all checks

.PHONY: build
build: ## Build (no-op for Python)
	@echo "no build step for ecs-sandbox"

.PHONY: docker-build
docker-build: ## Build Docker image
	@docker build -t ecs-sandbox:latest -f Dockerfile ../..

.PHONY: clean
clean: ## Clean build artifacts
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
