# Success Criteria

Checks that must pass before code can be merged. This is the CI gate.

## Quick Check

```bash
make check
# Runs fmt-check, lint, types, test across all projects
```

## Individual Checks

### Build

```bash
make build
# Builds all projects (hatchling for Python packages)
```

### Tests

```bash
make test
# Runs pytest across all projects
```

### Linting

```bash
make lint
# Runs Ruff across all projects
```

### Formatting

```bash
# Check formatting
make fmt-check

# Fix formatting
make fmt
```

### Type Checking

```bash
make types
# Runs ty across all projects
```

## Summary

| Check | Command | Tool |
|-------|---------|------|
| Format | `make fmt-check` | Black |
| Lint | `make lint` | Ruff |
| Types | `make types` | ty |
| Test | `make test` | pytest |
| Build | `make build` | hatchling |

## Docker

| Check | Command |
|-------|---------|
| Image build | `make docker-build` |

## Fixing Common Issues

### Formatting Failures

Run the formatter and commit:
```bash
make fmt
```

### Lint Warnings

Ruff errors are usually auto-fixable:
```bash
# Check what ruff would fix
uv run ruff check --fix .
```

### Test Failures

Run tests for a specific project:
```bash
make run-for PROJECT=apps/ecs-sandbox CMD=test
```

## Pre-commit

No pre-commit hooks configured. Run `make check` manually before pushing.
