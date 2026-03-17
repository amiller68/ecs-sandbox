.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: test
test: ## Run tests
	@uv run pytest || test $$? -eq 5

.PHONY: lint
lint: ## Run linting
	@uv run ruff check src/

.PHONY: fmt
fmt: ## Format code
	@uv run black src/

.PHONY: fmt-check
fmt-check: ## Check formatting
	@uv run black --check src/

.PHONY: types
types: ## Run type checking
	@uv run ty check src/

.PHONY: check
check: fmt-check lint types test ## Run all checks

.PHONY: build
build: ## Build (no-op)
	@echo "no build step for dev-cli"

.PHONY: clean
clean: ## Clean
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
