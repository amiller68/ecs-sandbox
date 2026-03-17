# Track cwd server-side

**Status:** Planned
**Labels:** web-terminal, quick-win, auto

## Objective

Make `cd` work across commands by tracking the working directory in the WebSocket session and prepending `cd {cwd} &&` to each exec payload.

## Implementation

1. Add a `cwd` variable to the WebSocket handler in `apps/ecs-sandbox/src/routers/web.py`, initialized to `/workspace`
2. Before sending each command, wrap it: `cd {cwd} && {cmd}`
3. When the user's command starts with `cd`, also append `&& pwd` to capture the resolved path
4. Parse the `pwd` output from the result and update the server-side `cwd`
5. Send the cwd back to the client in the output message so the prompt can show it

## Files

- `apps/ecs-sandbox/src/routers/web.py` — Add cwd tracking to `_handle_exec`
- `apps/ecs-sandbox/src/static/terminal.js` — Update prompt to show cwd from server response

## Acceptance Criteria

- [ ] `cd /tmp` then `pwd` returns `/tmp`
- [ ] `cd subdir` (relative) resolves correctly
- [ ] `cd` with no args goes to `/workspace` (or home)
- [ ] Invalid `cd /nonexistent` shows error, cwd unchanged
- [ ] Prompt displays current directory

## Verification

```
$ cd /tmp
$ pwd
/tmp
$ mkdir foo && cd foo
$ pwd
/tmp/foo
```
