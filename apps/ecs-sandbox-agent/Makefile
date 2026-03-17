.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: build
build: ## Build (no-op)
	@echo "no build step for ecs-sandbox-agent"

.PHONY: docker-build
docker-build: ## Build Docker image
	@docker build -t ecs-sandbox-agent:latest .

.PHONY: test
test: ## Run tests
	@echo "no tests yet"

.PHONY: lint
lint: ## Run linting
	@echo "no linting configured"

.PHONY: fmt
fmt: ## Format code
	@echo "no formatting configured"

.PHONY: fmt-check
fmt-check: ## Check formatting
	@echo "no formatting configured"

.PHONY: types
types: ## Check types
	@echo "no type checking configured"

.PHONY: check
check: ## Run all checks
	@echo "no checks configured"

.PHONY: clean
clean: ## Clean
	@echo "nothing to clean"
