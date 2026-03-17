# Success Criteria

CI gates that must pass before merge.

## Python (all apps and packages)

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

## Infrastructure

| Check | Command |
|-------|---------|
| Terraform plan | `make iac <stage> plan` |
| Terraform validate | `terraform validate` (run within each env) |

## Running All Checks

```bash
# Run everything
make check

# This runs fmt-check, lint, types, and test across all PROJECTS
```
