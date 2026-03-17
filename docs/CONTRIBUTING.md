# Contributing

## Setup

```bash
# Install dependencies
make install

# Start local services
make docker-up

# Run checks
make check
```

## Workflow

1. Create a branch: `git checkout -b feat/my-feature`
2. Make changes
3. Run checks: `make check`
4. Commit with Conventional Commits format: `feat(api): add batch exec endpoint`
5. Push and open a PR

## Adding a New App

1. Create directory under `apps/your-app/`
2. Add `pyproject.toml` with dependencies
3. Add `Makefile` with standard targets (`dev`, `build`, `test`, `check`, `fmt`, `lint`, `types`)
4. Register in root `pyproject.toml` workspace members
5. Register in root `Makefile` `PROJECTS` list
6. Add Dockerfile if it needs to be deployed
7. Add service definition in `iac/modules/aws/services/` if deployed to ECS

## Adding a New Package

1. Create directory under `packages/your-package/`
2. Add `pyproject.toml`
3. Register in root `pyproject.toml` workspace members and `[tool.uv.sources]`
4. Register in root `Makefile` `PROJECTS` list

## Code Quality Gates

All of these must pass before merge:

```bash
make fmt-check    # Black formatting
make lint         # Ruff linting
make types        # ty type checking
make test         # pytest
make build        # Build all projects
```

See [SUCCESS_CRITERIA.md](SUCCESS_CRITERIA.md) for details.

## Commit Message Format

```
<type>(<scope>): <summary>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

Scopes: `api`, `cli`, `client`, `agent`, `iac`, `cleanup`, `worker`
