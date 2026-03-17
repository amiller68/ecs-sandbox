---
description: Run project checks (build, test, lint, format). Use when validating code quality, preparing for merge, or verifying changes pass CI.
allowed-tools:
  - Bash(make:*)
  - Bash(uv:*)
  - Bash(cat:*)
  - Bash(ls:*)
  - Read
  - Glob
  - Grep
---

Run the full success criteria checks to validate code quality.

## Steps

1. Run `make check` from the repo root. This runs fmt-check, lint, types, and test across all projects.

2. If formatting checks fail, auto-fix with `make fmt`, then re-run `make check`.

3. If lint errors are auto-fixable, run `uv run ruff check --fix .` from the affected project directory, then re-run `make check`.

4. Report a summary of pass/fail status for each check.

5. If any checks fail that cannot be auto-fixed, report what needs manual attention.

This is the gate for all PRs — all checks must pass before merge.
