# Contributing

Guide for both human contributors and AI agents working on this project.

## For All Contributors

### Getting Started

1. Clone the repository
2. Install dependencies: `make install`
3. Start local services: `make setup`
4. Run checks: `make check`
5. Start development: `make dev`

### Making Changes

1. Create a feature branch from `main`
2. Make your changes following the patterns in `docs/PATTERNS.md`
3. Run checks: `make check`
4. Commit with Conventional Commits format
5. Open a pull request

### Commit Message Format

```
<type>(<scope>): <summary>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

Scopes: `api`, `cli`, `client`, `agent`, `iac`, `cleanup`, `worker`, `web`

Examples:
```
feat(api): add batch exec endpoint
fix(cleanup): handle orphan containers without session rows
docs: add deployment guide
chore(iac): update ECS task definition memory limits
```

### Adding a New App

1. Create directory under `apps/your-app/`
2. Add `pyproject.toml` with dependencies
3. Add `Makefile` with standard targets (`dev`, `build`, `test`, `check`, `fmt`, `lint`, `types`)
4. Register in root `pyproject.toml` workspace members
5. Register in root `Makefile` `PROJECTS` list
6. Add Dockerfile if it needs to be deployed

### Adding a New Package

1. Create directory under `packages/your-package/`
2. Add `pyproject.toml`
3. Register in root `pyproject.toml` workspace members and `[tool.uv.sources]`
4. Register in root `Makefile` `PROJECTS` list

## For AI Agents

### Context to Gather First

Before making changes, read:
- `CLAUDE.md` — Project overview and quick commands
- `docs/PATTERNS.md` — Coding conventions
- `docs/SUCCESS_CRITERIA.md` — CI checks that must pass
- Related code files to understand existing patterns

### Workflow

1. **Understand** — Read the task and relevant code
2. **Plan** — Break down into small steps
3. **Implement** — Follow existing patterns
4. **Verify** — Run `make check`
5. **Commit** — Clear, atomic commits with Conventional Commits format

### Constraints

- Don't modify CI/CD configuration without approval
- Don't add new dependencies without discussion
- Don't refactor unrelated code
- Don't skip tests or use `--no-verify`
- Never run `pytest`, `black`, `ruff` directly — use `make` targets

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

## Code Review

- CI must pass before merge
- Changes reviewed by parent session or maintainer
- Squash commits on merge when appropriate
