# Local Development

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Docker — for running sandbox containers and local services
- (Optional) [1Password CLI](https://developer.1password.com/docs/cli/) — for secrets in staging/production

## Setup

```bash
# Clone the repo
git clone <repo-url> && cd ecs-sandbox

# Install all Python dependencies
make install
```

This runs `uv sync --all-packages`, which installs all workspace members:
- `apps/ecs-sandbox` (control plane)
- `apps/ecs-sandbox-agent` (container sidecar)
- `apps/dev-cli` (test agent)
- `packages/ecs-sandbox-client` (client library)

## Running Locally

### Option 1: Docker Compose (recommended)

Starts the full stack: control plane, worker, scheduler, and Redis.

```bash
make docker-up
```

Services:
- Control plane: http://localhost:8000
- Redis: localhost:6379

To stop:

```bash
make docker-down
```

### Option 2: Dev mode with tmux

```bash
make dev
```

This starts all services in a tmux session with hot-reload.

### Option 3: Run services individually

```bash
# Control plane
cd apps/ecs-sandbox && make dev

# Worker (in another terminal)
cd apps/ecs-sandbox && make worker

# Scheduler (in another terminal)
cd apps/ecs-sandbox && make scheduler
```

## Testing the Sandbox

### With curl

```bash
# Create a session
curl -X POST http://localhost:8000/sandbox \
  -H "X-Sandbox-Secret: dev-secret-change-me-in-prod" \
  -H "Content-Type: application/json" \
  -d '{"id": "test-session-001", "ttl_seconds": 1800}'

# Run a command
curl -X POST http://localhost:8000/sandbox/test-session-001/exec \
  -H "X-Sandbox-Secret: dev-secret-change-me-in-prod" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "echo hello world", "sync": true}'

# Check history
curl http://localhost:8000/sandbox/test-session-001/history \
  -H "X-Sandbox-Secret: dev-secret-change-me-in-prod"

# Destroy session
curl -X DELETE http://localhost:8000/sandbox/test-session-001 \
  -H "X-Sandbox-Secret: dev-secret-change-me-in-prod"
```

### With the Dev CLI

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Interactive chat with the agent
uv run dev-cli chat "Write a Python script that counts words in a file"

# Or run a single command
uv run dev-cli exec test-session-001 "ls -la /workspace"
```

## Environment Variables

For local development, the Docker Compose file sets all required variables. If running outside Docker:

```bash
export SANDBOX_SECRET=dev-secret-change-me-in-prod
export SANDBOX_IMAGE=ecs-sandbox-agent:latest
export DB_PATH=/tmp/ecs-sandbox.db
export WORKSPACE_BACKEND=none          # or 'efs' if you have a local mount
export MAX_CONTAINERS=10
export DEFAULT_TTL_SECONDS=1800
export DEBUG=true
```

## Running Tests

```bash
# All tests
make test

# Just the control plane
cd apps/ecs-sandbox && make test

# Just the client library
cd packages/ecs-sandbox-client && make test
```

## Code Quality

```bash
# Run all checks (format, lint, types, test)
make check

# Format code
make fmt

# Check formatting without changes
make fmt-check

# Lint
make lint

# Type check
make types
```

## Troubleshooting

**"Container ceiling reached" (503)**
- Increase `MAX_CONTAINERS` or destroy idle sessions
- Check for orphan containers: `docker ps --filter label=ecs-sandbox.session_id`

**SQLite "database is locked"**
- Ensure only one writer process at a time
- Check that WAL mode is enabled (it should be set automatically on connection open)
- Increase `PRAGMA busy_timeout` if needed

**Docker socket permission denied**
- Ensure the Docker socket is mounted: `-v /var/run/docker.sock:/var/run/docker.sock`
- On Linux, add your user to the `docker` group
