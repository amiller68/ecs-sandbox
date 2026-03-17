# draft

Create a draft PR for the current branch.

## When to use

- When work is ready for review
- When asked to "open a PR" or "create a draft"

## Steps

1. Run `make check` to ensure all checks pass
2. Stage changes: `git add <files>`
3. Commit with Conventional Commits format: `<type>(<scope>): <summary>`
4. Push branch: `git push -u origin <branch>`
5. Create draft PR: `gh pr create --draft --title "..." --body "..."`

## PR body format

```markdown
## Summary
- Brief description of changes

## Test plan
- [ ] `make check` passes
- [ ] Manual testing steps if applicable
```

## Scopes

Use these scopes for commit messages: `api`, `cli`, `client`, `agent`, `iac`, `cleanup`, `worker`, `docs`
