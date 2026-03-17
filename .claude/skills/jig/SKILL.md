---
description: Manage jig worktrees and workers. Use to create worktrees, spawn workers, monitor progress, review and merge completed work.
allowed-tools:
  - Bash(jig:*)
  - Bash(tmux:*)
  - Bash(git status)
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git branch:*)
  - Read
  - Glob
  - Grep
---

Manage jig worktrees and parallel Claude Code workers.

## Commands

### Worktree management
```bash
jig create <name>              # Create a new worktree
jig list                       # List all worktrees
jig open <name>                # cd into a worktree
jig remove <name>              # Remove a worktree
jig home                       # cd back to base repo
```

### Worker spawning
```bash
jig spawn <name> --context "<task description>" --auto   # Create worktree + launch Claude
jig ps                         # Show status of all workers
jig attach <name>              # Attach to a worker's tmux session
jig resume <name>              # Relaunch a dead worker
jig kill <name>                # Kill a running worker
jig nuke                       # Kill all workers and clean state
```

### Review and merge
```bash
jig review <name>              # Show diff for review
jig merge <name>               # Merge reviewed worktree into current branch
```

### Issues
```bash
jig issues                     # List all issues
jig issues <id>                # Show a specific issue
jig issues --status planned    # Filter by status
jig issues create              # Create a new issue interactively
jig issues status <id> <status>  # Update issue status
```

## Workflow

1. **Discover work**: `jig issues` or `/issues`
2. **Spawn workers**: `jig spawn <name> --context "<details>" --auto`
3. **Monitor**: `jig ps`
4. **Review**: `jig review <name>`
5. **Merge**: `jig merge <name>`

## Configuration

Config lives in `jig.toml`:
- `worktree.base` — base branch for new worktrees
- `worktree.on_create` — command to run after worktree creation (e.g. `make install`)
- `worktree.copy` — gitignored files to copy to new worktrees (e.g. `.env`)
- `spawn.auto` — auto-start Claude when spawning
- `agent.type` — agent framework (`claude` or `cursor`)

## Tips

- Keep `--context` detailed — it's the worker's entire prompt
- Spawn 2-4 workers at a time to avoid resource contention
- Workers can't see each other's changes — keep tasks independent
- Always `jig review` before `jig merge`
