# Documentation Index

Central hub for project documentation. AI agents should read this first.

## Quick Start

```bash
# Install dependencies
make install

# Start local services (Redis)
make setup

# Start dev server + worker + scheduler
make dev

# Run all checks
make check
```

## Documentation

| Document | Purpose |
|----------|---------|
| [PATTERNS.md](./PATTERNS.md) | Coding conventions and patterns |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute (agents + humans) |
| [SUCCESS_CRITERIA.md](./SUCCESS_CRITERIA.md) | CI checks that must pass |

## Services

| Service | Port | Description |
|---------|------|-------------|
| ecs-sandbox | 8000 | FastAPI control plane |
| ecs-sandbox-agent | 2222 | Sidecar inside each sandbox container |
| dev-cli | — | CLI agent for testing the sandbox |
| worker | — | Taskiq background job worker |
| scheduler | — | Taskiq cron scheduler (cleanup reaper) |
| redis | 6379 | Job queue broker |

## For AI Agents

You are an autonomous coding agent working on a focused task.

### Workflow

1. **Understand** — Read the task description and relevant docs
2. **Explore** — Search the codebase to understand context
3. **Plan** — Break down work into small steps
4. **Implement** — Follow existing patterns in `PATTERNS.md`
5. **Verify** — Run checks from `SUCCESS_CRITERIA.md`
6. **Commit** — Clear, atomic commits

### Guidelines

- Use `make` targets — never run `pytest`, `black`, `ruff` directly
- Follow existing code patterns and conventions
- Make atomic commits (one logical change per commit)
- Add tests for new functionality
- Update documentation if behavior changes
- Session IDs are caller-supplied — the sandbox never generates or lists them
- If blocked, commit what you have and note the blocker

### When Complete

Your work will be reviewed and merged by the parent session.
Ensure all checks pass before finishing.
