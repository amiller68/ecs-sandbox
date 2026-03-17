PROJECTS := apps/ecs-sandbox apps/ecs-sandbox-agent apps/dev-cli packages/ecs-sandbox-client

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Run-all targets (operate on all projects):'
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ && !/^[a-zA-Z_-]+-%:/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Available projects:'
	@for project in $(PROJECTS); do \
	    echo "  - $$project"; \
	done

# run a make command in the given directory
run-for:
	@if [ -d "./$(PROJECT)" ]; then \
		if [ -f "./$(PROJECT)/Makefile" ]; then \
			cd ./$(PROJECT) && make $(CMD); \
		else \
			echo "Error: Makefile not found in ./$(PROJECT) directory"; \
			exit 1; \
		fi; \
	else \
		echo "Error: Directory ./$(PROJECT) does not exist"; \
		exit 1; \
	fi

.PHONY: install
install: ## Install dependencies for all projects
	@uv sync --all-packages
	@pnpm install

.PHONY: setup
setup: ## Start local dev services (Redis)
	@$(MAKE) -C apps/ecs-sandbox setup

.PHONY: teardown
teardown: ## Stop local dev services
	@$(MAKE) -C apps/ecs-sandbox teardown

.PHONY: dev
dev: ## Run dev server + worker + scheduler via turbo
	@pnpm dev

.PHONY: check
check: ## Check all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=check; \
	done

.PHONY: build
build: ## Build all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=build; \
	done

.PHONY: test
test: ## Run tests for all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=test; \
	done

.PHONY: lint
lint: ## Run linters for all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=lint; \
	done

.PHONY: fmt
fmt: ## Format all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=fmt; \
	done

.PHONY: fmt-check
fmt-check: ## Check formatting for all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=fmt-check; \
	done

.PHONY: types
types: ## Run type checking for all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=types; \
	done

.PHONY: docker-build
docker-build: ## Build Docker images for all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=docker-build; \
	done

.PHONY: docker-up
docker-up: ## Start docker-compose with vault secrets (rebuilds images)
	@./bin/vault run --stage development -- docker compose up --build

.PHONY: docker-down
docker-down: ## Stop docker-compose
	@docker compose down

.PHONY: docker-clean
docker-clean: ## Remove docker images and volumes
	@docker compose down -v --rmi local

.PHONY: clean
clean: ## Clean all projects
	@for project in $(PROJECTS); do \
		$(MAKE) run-for PROJECT=$$project CMD=clean; \
	done

.PHONY: docker-push
docker-push: ## Push Docker images to ECR (requires vault)
	@./bin/vault run -- ./bin/docker push ecs-sandbox
	@./bin/vault run -- ./bin/docker push ecs-sandbox-agent

# Terraform Cloud management
.PHONY: tfc
tfc: ## Terraform Cloud management - pass all arguments after 'tfc' to the script
	@./bin/tfc $(filter-out $@,$(MAKECMDGOALS))

# Infrastructure management
.PHONY: iac
iac: ## Infrastructure management - run terraform with vault secrets
	@./bin/iac $(filter-out $@,$(MAKECMDGOALS))

# ECS operations
.PHONY: ecs
ecs: ## ECS operations (ssh, deploy) - usage: make ecs <command> <stage> <service>
	@./bin/vault run -- ./bin/ecs $(filter-out $@,$(MAKECMDGOALS))

# Deploy all services to a stage
.PHONY: deploy
deploy: ## Deploy all services - usage: make deploy <stage>
	@STAGE=$(word 2,$(MAKECMDGOALS)); \
	./bin/vault run -- ./bin/ecs deploy $$STAGE ecs-sandbox --wait

# Worktree management
.PHONY: worktree-create
worktree-create: ## Create a new worktree (NAME=<name> [BRANCH=<branch>])
	@./bin/worktree create $(NAME) $(BRANCH)

.PHONY: worktree-list
worktree-list: ## List active worktrees
	@./bin/worktree list

.PHONY: worktree-remove
worktree-remove: ## Remove a worktree (NAME=<name>)
	@./bin/worktree remove $(NAME)

.PHONY: worktree-cleanup
worktree-cleanup: ## Remove all worktrees
	@./bin/worktree cleanup

.PHONY: ports
ports: ## Show current port assignments
	@./bin/worktree-ports

# Catch additional arguments
%:
	@:
