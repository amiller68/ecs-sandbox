# PTY-based sessions in sidecar

**Status:** Planned
**Labels:** web-terminal, sidecar

## Objective

Replace one-shot exec calls with a persistent PTY shell process in the sidecar agent, giving the web terminal real shell semantics (cwd, env vars, aliases, job control).

## Implementation

1. Add a `/shell` WebSocket endpoint to the sidecar agent (`apps/ecs-sandbox-agent/agent.py`)
   - On connect: spawn a bash process with a PTY via `pty.openpty()` or `asyncio.create_subprocess_exec` with PTY
   - Bidirectional: client sends raw bytes, server sends raw PTY output
   - Handle resize events (SIGWINCH)
2. Update the control plane's web router to proxy the WebSocket to the sidecar's `/shell` endpoint instead of using the insert-event/poll-result flow
3. Update `terminal.js` to send raw keystrokes instead of line-buffered input
4. Keep the exec-based flow as a fallback for the REST API

## Files

- `apps/ecs-sandbox-agent/agent.py` — Add `/shell` WebSocket endpoint with PTY
- `apps/ecs-sandbox/src/routers/web.py` — Proxy WebSocket to sidecar
- `apps/ecs-sandbox/src/static/terminal.js` — Switch to raw mode

## Acceptance Criteria

- [ ] Shell state persists: `export FOO=bar` then `echo $FOO` returns `bar`
- [ ] `cd` works natively
- [ ] Tab completion works
- [ ] Ctrl-C interrupts running commands
- [ ] Terminal resize propagates
- [ ] REST exec API still works independently

## Verification

Full interactive shell experience — vim, htop, piped commands, background jobs.
