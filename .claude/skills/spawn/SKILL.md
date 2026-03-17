# spawn

Spawn parallel workers for independent tasks.

## When to use

- When multiple independent tasks can be done in parallel
- When asked to "work on X and Y at the same time"

## How

Use `jig spawn` to launch parallel workers:

```bash
jig spawn "task description" --context "relevant context" --auto
```

## Rules

- Only spawn for truly independent tasks (no shared file edits)
- Include full context in the spawn command — workers don't share memory
- Each worker should own its own set of files
- Coordinate via `task.log.md` if needed
