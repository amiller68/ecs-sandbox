# check

Run all CI checks across the monorepo.

## When to use

- Before committing or opening a PR
- After making changes to validate nothing is broken
- When asked to "check", "validate", or "verify" the code

## Steps

1. Run `make check` from the repo root
2. This runs `fmt-check`, `lint`, `types`, and `test` across all projects
3. If any check fails, fix the issue and re-run

## Per-project checks

If you only changed one project, you can run checks for just that project:

```bash
cd apps/ecs-sandbox && make check
cd apps/dev-cli && make check
cd packages/ecs-sandbox-client && make check
```

## Individual checks

```bash
make fmt-check    # Black formatting
make lint         # Ruff linting
make types        # ty type checking
make test         # pytest
```
