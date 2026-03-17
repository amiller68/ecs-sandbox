# Worktree-Based Parallel Development

**Status:** Complete
**Labels:** dx, infrastructure, testing, auto

## Objective

Enable multiple developers (or Claude Code agents) to run isolated dev environments simultaneously by adopting the worktree + port-allocation pattern from [generic](https://github.com/amiller68/generic). Add Playwright MCP as the e2e testing layer so agents can verify their work against their own dev server.

## Background

Currently, `bin/dev` hardcodes the tmux session name (`ecs-sandbox-dev`) and all services bind to fixed ports (8000 for the API, 6379 for Redis). This means only one dev environment can run at a time on a given machine. For parallel development — especially with `jig`/`spawn` workflows that create worktrees — each worktree needs its own server, worker, scheduler, and Redis index without port conflicts.

The `generic` repo solves this with three scripts:
- `bin/worktree` — create/list/remove git worktrees in `.worktrees/`
- `bin/worktree-ports` — auto-allocate ports (8000–8009) and derive per-branch Redis DB indices and SQLite paths
- `bin/dev` — start tmux sessions using the allocated ports

## Implementation

### 1. Add `bin/worktree-ports` script

Allocate unique ports and derive per-worktree configuration:

- Scan ports 8000–8009 via `lsof` to find an available one
- Derive `REDIS_DB_INDEX` from port offset (e.g., port 8002 → index 2)
- Derive `DB_PATH` from branch name (e.g., `data/ecs-sandbox-feat-foo.db`)
- Export env vars: `BACKEND_PORT`, `REDIS_DB_INDEX`, `DB_PATH`
- Write a `.dev-server` file documenting the active config

### 2. Add `bin/worktree` script

Manage worktrees for parallel development:

- `worktree create <name> [branch]` — create worktree in `.worktrees/<name>`
- `worktree list` — list active worktrees
- `worktree remove <name>` — clean up a worktree
- `worktree cleanup` — remove all worktrees

### 3. Update `bin/dev` to use allocated ports

- Source `bin/worktree-ports` before starting services
- Use `$BACKEND_PORT` for the API server
- Pass `$REDIS_DB_INDEX` to Redis-backed services (worker, scheduler)
- Pass `$DB_PATH` to the server and worker
- Derive tmux session name from branch (e.g., `ecs-sandbox-feat-foo`)

### 4. Update `apps/ecs-sandbox` to respect port/DB config

- Ensure the FastAPI server reads `PORT` or `BACKEND_PORT` env var (currently may be hardcoded to 8000 in the Makefile `dev` target)
- Ensure `DB_PATH` is respected for per-worktree SQLite databases
- Ensure `REDIS_URL` supports a DB index suffix (e.g., `redis://localhost:6379/2`)

### 5. Update `docker-compose.yml` for worktree awareness

- Use `${BACKEND_PORT:-8000}` for the API port mapping
- Use `${REDIS_DB_INDEX:-0}` in Redis URL env vars
- Use `${DB_PATH:-/data/ecs-sandbox.db}` for database path
- Container names already use `${PROJECT_NAME}` prefix — this is good

### 6. Add `bin/utils` helpers (if not already present)

- Colored output functions (`print_header`, `print_success`, `print_warning`, `print_error`)
- Already partially exists — extend as needed

### 7. Update root Makefile

Add convenience targets:

```makefile
worktree-create:  ## Create a new worktree
worktree-list:    ## List active worktrees
worktree-remove:  ## Remove a worktree
ports:            ## Show current port assignments
```

### 8. Playwright MCP for e2e testing

Add [`@playwright/mcp`](https://github.com/microsoft/playwright-mcp) as a project-scoped MCP server so Claude Code agents can drive a browser against their worktree's dev server for e2e verification.

**Project MCP config** (`.claude/settings.json` or `.mcp.json`):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest", "--headless"]
    }
  }
}
```

**How it works with worktrees:**

- Each worktree runs its dev server on a unique port (from step 1)
- The `.dev-server` file records the allocated `BACKEND_PORT`
- Agents use Playwright MCP's `browser_navigate` tool to hit `http://localhost:$BACKEND_PORT`
- No port conflicts — each agent's browser talks to its own isolated server

**Key Playwright MCP tools for API e2e testing:**

| Tool | Use |
|------|-----|
| `browser_navigate` | Hit API endpoints or any web UI |
| `browser_snapshot` | Read structured page content (accessibility tree, not pixels) |
| `browser_click` / `browser_type` | Interact with any web UI |
| `browser_console_messages` | Capture console errors during testing |
| `browser_take_screenshot` | Visual verification when needed |
| `browser_generate_playwright_test` | Record reusable test scripts |

**e2e test workflow for agents:**

1. Agent starts dev server via `make dev` (gets port from `bin/worktree-ports`)
2. Agent reads `.dev-server` to discover its `BACKEND_PORT`
3. Agent uses `browser_navigate` to `http://localhost:$BACKEND_PORT/docs` (FastAPI Swagger UI)
4. Agent exercises API flows through the browser — create session, execute command, check status
5. Agent uses `browser_snapshot` to verify responses
6. Agent can also hit raw API endpoints and verify JSON responses

**Optional: add a `make e2e` target** that:
- Starts the dev server in the background
- Runs a Playwright test suite against the allocated port
- Tears down after

### 9. Add `bin/agent-watch.sh` or similar for agent dev loops

Tie it all together — a script that agents can invoke to:
1. Start dev services for the current worktree
2. Configure Playwright MCP to point at the right port
3. Run checks + e2e verification
4. Report results

## Files

- `bin/worktree` — New script for worktree management
- `bin/worktree-ports` — New script for port allocation and env derivation
- `bin/dev` — Update to source worktree-ports and use dynamic config
- `bin/utils` — Extend with any missing helper functions
- `Makefile` — Add worktree and e2e convenience targets
- `docker-compose.yml` — Parameterize ports and DB paths
- `apps/ecs-sandbox/Makefile` — Ensure dev target respects `BACKEND_PORT`
- `.gitignore` — Add `.worktrees/` and `.dev-server`
- `.claude/settings.json` or `.mcp.json` — Playwright MCP server config
- `package.json` — Add `@playwright/mcp` as a dev dependency

## Acceptance Criteria

- [ ] Two worktrees can run `make dev` simultaneously without port conflicts
- [ ] Each worktree gets its own SQLite database and Redis DB index
- [ ] `bin/worktree create/list/remove` work correctly
- [ ] `bin/worktree-ports` auto-allocates available ports
- [ ] `.dev-server` file documents active configuration per worktree
- [ ] Existing single-worktree `make dev` workflow still works (defaults to port 8000, DB index 0)
- [ ] Playwright MCP is configured as a project-scoped MCP server
- [ ] An agent in a worktree can use Playwright MCP to navigate to its dev server and verify API responses
- [ ] No conflicts when multiple agents run Playwright MCP against different worktree ports

## Verification

```bash
# Create two worktrees
make worktree-create NAME=feat-a
make worktree-create NAME=feat-b

# Start dev in each (separate terminals)
cd .worktrees/feat-a && make dev
cd .worktrees/feat-b && make dev

# Verify different ports
curl localhost:8000/health  # feat-a
curl localhost:8001/health  # feat-b

# In a Claude Code session within feat-a's worktree:
# - Use browser_navigate to http://localhost:8000/docs
# - Use browser_snapshot to verify Swagger UI loads
# - Use browser_navigate to http://localhost:8000/health
# - Use browser_snapshot to verify {"status": "ok"} response

# Clean up
make worktree-remove NAME=feat-a
make worktree-remove NAME=feat-b
```
