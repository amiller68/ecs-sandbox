# Hot-rebuild agent image during dev

**Status:** Planned
**Labels:** dx, auto

## Objective

Automatically rebuild the `ecs-sandbox-agent` Docker image when source files change during development, so the dev loop doesn't require manual rebuilds.

## Implementation

1. Add a file watcher (fswatch or similar) in `bin/dev` or as a separate tmux pane
2. Watch `apps/ecs-sandbox-agent/` for changes to `*.py`, `Dockerfile`, `requirements.txt`
3. On change: run `docker build -t ecs-sandbox-agent:latest apps/ecs-sandbox-agent/`
4. Optionally: stop + recreate any running sandbox containers using the old image

Alternative: use a turbo task with `inputs` glob so `turbo dev` handles rebuild detection.

## Files

- `bin/dev` — Add watcher pane or integrate with turbo
- `apps/ecs-sandbox-agent/Makefile` — Ensure `docker-build` target exists (already does)

## Acceptance Criteria

- [ ] Editing `agent.py` triggers an automatic image rebuild
- [ ] Dev server logs show the rebuild happening
- [ ] New sessions after rebuild use the updated image

## Verification

1. Start `make dev`
2. Edit `apps/ecs-sandbox-agent/agent.py` (add a comment)
3. See rebuild in logs
4. Create a new session — it uses the rebuilt image
