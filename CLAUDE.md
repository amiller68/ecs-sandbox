# Project Guide

Remote sandbox execution environment for AI agents. Manages ephemeral Docker containers via a REST API backed by SQLite on EFS.

## Quick Reference

```bash
make install              # Install all dependencies (uv sync + pnpm install)
make setup                # Start local dev services (Redis)
make dev                  # Start all services via turbo (server + worker + scheduler)
make check                # Run fmt-check, lint, types, test across all projects
make build                # Build all projects
make test                 # Run tests
make fmt                  # Format all code (Black)
make lint                 # Lint all code (Ruff)
make types                # Type check all code (ty)
make teardown             # Stop local dev services
make docker-up            # Start docker-compose stack with vault secrets
make docker-down          # Stop docker-compose stack
make ports                # Show current port assignments
```

## Project Structure

```
apps/
  ecs-sandbox/             # FastAPI control plane (port 8000)
  ecs-sandbox-agent/       # Sidecar that runs inside each sandbox container (port 2222)
  dev-cli/                 # Development CLI with agent for testing
packages/
  ecs-sandbox-client/      # Typed Python client library (httpx + pydantic)
iac/                       # Terraform (ECS, EFS, ECR, networking)
bin/                       # Dev and deploy scripts (dev, worktree-ports, vault, etc.)
docs/                      # Architecture, patterns, and dev guides
issues/                    # File-based issue tracking
```

## Documentation

- `docs/index.md` — Documentation hub and agent instructions
- `docs/PATTERNS.md` — Coding conventions
- `docs/SUCCESS_CRITERIA.md` — CI checks
- `docs/CONTRIBUTING.md` — Contribution guide

## Issues

Track work items in `issues/`. See `issues/README.md` for the convention.

## Constraints

- Python 3.12+, uv workspace mode
- All API endpoints require `X-Sandbox-Secret` header
- Session IDs are caller-supplied UUIDs — sessions are not enumerable
- Never run `pytest`, `black`, `ruff`, `ty` directly — use `make` targets or `uv run`
- Pin major versions in `pyproject.toml`: `"fastapi>=0.115,<1"`
- Use `uv` workspace for internal dependencies: `ecs-sandbox-client = { workspace = true }`
- Background jobs use Taskiq + Redis with distributed locking
- Commit format: `<type>(<scope>): <summary>` (Conventional Commits)

## Do Not

- Do not run formatters/linters directly — always use `make` targets
- Do not edit `.env.project` `PROJECT_NAME` after initialization
- Do not commit `.env` files or secrets
- Do not mock SQLite in tests — use an in-memory database
- Do not skip CI checks with `--no-verify`
