# ecs-sandbox

Remote sandbox execution environment for AI agents. Manages ephemeral Docker containers via a REST API backed by SQLite on EFS.

## Quick Reference

```bash
make install              # Install all Python dependencies (uv sync)
make dev                  # Start all services in tmux
make check                # Run fmt-check, lint, types, test across all projects
make build                # Build all projects
make test                 # Run tests
make fmt                  # Format all code
make docker-up            # Start docker-compose stack (app + worker + scheduler + redis)
make docker-down          # Stop docker-compose stack
```

## Project Structure

```
apps/
  ecs-sandbox/             # FastAPI control plane (main service)
  ecs-sandbox-agent/       # Sidecar that runs inside each sandbox container
  dev-cli/                 # Development CLI with simple agent for testing
packages/
  ecs-sandbox-client/      # Typed Python client library
iac/                       # Terraform (ECS, EFS, ECR, networking)
bin/                       # Dev and deploy scripts (dev, vault, iac, tfc)
docs/                      # Architecture, API, deployment, and dev guides
```

## Tech Stack

- **Language:** Python 3.12+
- **Web framework:** FastAPI
- **Package manager:** uv (workspace mode)
- **Database:** SQLite (aiosqlite) on EFS
- **Background jobs:** Taskiq + Redis
- **Containers:** Docker + runc
- **Deployment:** ECS Fargate, Terraform Cloud
- **Secrets:** 1Password

## Conventions

- **Commit format:** `<type>(<scope>): <summary>` (Conventional Commits)
- **Python formatting:** Black
- **Python linting:** Ruff
- **Python types:** ty (mypy successor)
- **Testing:** pytest + pytest-asyncio
- **Never** run `pytest`, `black`, `ruff` directly — use `make` targets or `uv run`
- **Never** edit `.env.project` `PROJECT_NAME` after initialization
- All API endpoints require `X-Sandbox-Secret` header
- Session IDs are caller-supplied UUIDs — sessions are not enumerable

## Key Files

- `/CLAUDE.md` — this file (quick project reference)
- `/docs/index.md` — documentation hub
- `/docs/ARCHITECTURE.md` — system architecture and data flow
- `/docs/API.md` — REST API reference
- `/docs/PATTERNS.md` — coding conventions
- `/.claude/settings.json` — Claude Code permission matrix
- `/.env.project` — project config (name, DNS, services)

## Services

| Service | Port | Description |
|---------|------|-------------|
| ecs-sandbox | 8000 | FastAPI control plane |
| ecs-sandbox-agent | 2222 | Sidecar inside each sandbox container |
| dev-cli | — | CLI agent for testing the sandbox |
| worker | — | Taskiq background job worker |
| scheduler | — | Taskiq cron scheduler (cleanup reaper) |
| redis | 6379 | Job queue broker |
