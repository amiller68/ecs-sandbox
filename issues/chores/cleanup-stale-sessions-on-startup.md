# Clean up stale sessions on server startup

**Status:** Planned
**Labels:** reliability

## Objective

On server startup, mark any `active` sessions in the DB as `destroyed` and remove their containers. After a restart, old container IPs are stale and sessions are unreachable — they should be cleaned up automatically instead of requiring manual DB edits.

## Implementation

1. In `apps/ecs-sandbox/src/server.py` lifespan, after Docker connects:
   - Query all `active` sessions from the DB
   - For each, attempt to remove the container (ignore NotFound)
   - Mark them as `destroyed`
2. Log how many stale sessions were cleaned up

## Files

- `apps/ecs-sandbox/src/server.py` — Add cleanup step in lifespan startup

## Acceptance Criteria

- [ ] Stale `active` sessions from a previous run are destroyed on startup
- [ ] Orphaned containers are removed
- [ ] Clean startup with no stale sessions logs "0 stale sessions cleaned"
- [ ] Normal operation unaffected — sessions created after startup work fine

## Verification

1. Start server, create a session via web terminal
2. Kill server (don't graceful shutdown)
3. Restart server — see log: "Cleaned up 1 stale session(s)"
4. DB shows no active sessions from before restart
