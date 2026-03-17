# ecs-sandbox

A remote sandbox execution environment for AI agents. Provides ephemeral, isolated Docker containers accessible via REST API — designed for agents that need to run code, manipulate files, and execute shell commands in a controlled environment.

## What It Does

- **Creates isolated sandboxes** — each session gets its own Docker container with a dedicated filesystem, process tree, and session history
- **Async command execution** — submit commands via API, poll for results; commands execute sequentially per session to maintain coherent shell state
- **File and git operations** — read/write files, clone repos, commit changes inside the sandbox
- **Automatic cleanup** — idle sessions are reaped after a configurable TTL; orphan containers are swept on a cron schedule
- **Single-file state** — SQLite on EFS, no Postgres or Redis required for the core service (Redis used only for background job scheduling)

## Architecture

```
Caller (agent / CLI)
  └── REST API (X-Sandbox-Secret auth)
        └── ecs-sandbox (FastAPI on ECS)
              ├── Docker daemon
              │    └── per-session containers (ecs-sandbox-agent sidecar)
              └── SQLite on EFS
                   ├── sessions table
                   └── events table
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker
- (Optional) 1Password CLI for secrets

### Install & Run

```bash
# Install all dependencies
make install

# Start the full stack locally (app + worker + scheduler + redis)
make docker-up

# Or run the dev server directly
make dev
```

### Test with the Dev CLI

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run the agent
uv run dev-cli chat "Write a Python script that prints the first 20 fibonacci numbers"
```

The dev CLI spins up a simple agent that uses the sandbox as a tool — it can execute code, read/write files, and inspect results.

## API Overview

All endpoints require `X-Sandbox-Secret: <secret>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sandbox` | Create a new session |
| `POST` | `/sandbox/{id}/exec` | Submit a command (async) |
| `GET` | `/sandbox/{id}/events/{seq}` | Get event result |
| `GET` | `/sandbox/{id}/history` | Get session history |
| `GET` | `/sandbox/{id}/fs` | Read a file |
| `POST` | `/sandbox/{id}/fs` | Write a file |
| `DELETE` | `/sandbox/{id}/fs` | Delete a file |
| `POST` | `/sandbox/{id}/git/clone` | Clone a repository |
| `POST` | `/sandbox/{id}/git/commit` | Commit changes |
| `DELETE` | `/sandbox/{id}` | Destroy session |

See [docs/API.md](docs/API.md) for the full reference.

## Project Structure

```
apps/
  ecs-sandbox/                # FastAPI control plane
  ecs-sandbox-agent/          # Sidecar running inside each sandbox container
  dev-cli/                    # Development CLI with test agent
packages/
  ecs-sandbox-client/         # Typed Python client library
iac/                          # Terraform for ECS, EFS, ECR, networking
bin/                          # Dev and deploy scripts
docs/                         # Full documentation
```

## Deployment

The service deploys to AWS ECS (Fargate) with EFS for durable SQLite storage. Infrastructure is managed via Terraform Cloud.

```bash
# Set up Terraform Cloud workspaces
make tfc up

# Deploy infrastructure
make iac production apply

# Build and push Docker images
make docker-build
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full deployment guide.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design, data flow, session lifecycle
- [API Reference](docs/API.md) — complete REST API documentation
- [Local Development](docs/LOCAL_DEV.md) — setup, running, and testing locally
- [Deployment](docs/DEPLOYMENT.md) — ECS deployment with Terraform
- [Patterns](docs/PATTERNS.md) — coding conventions and project patterns
- [Contributing](docs/CONTRIBUTING.md) — how to add features and submit changes
