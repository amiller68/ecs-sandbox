# Persistent Terminal Sessions

**Status:** Planned

## Background

Each command in the web terminal currently runs as an independent exec call with a fixed cwd of `/workspace`. Shell state (working directory, env vars, aliases) doesn't persist between commands. This makes `cd`, `export`, and other stateful commands useless.

## Design

Two-phase approach: first track cwd server-side as a quick fix, then move to a PTY-based session in the sidecar for full shell semantics.

## Tickets

| # | Ticket | Status |
|---|--------|--------|
| 0 | [Track cwd server-side](./0-track-cwd.md) | Planned |
| 1 | [PTY-based sessions in sidecar](./1-pty-sessions.md) | Planned |

## Success Criteria

- [ ] `cd /tmp && pwd` in one command, then `pwd` in the next, both show `/tmp`
- [ ] Environment variables set with `export` persist across commands
- [ ] Interactive programs (vim, top) work in the terminal
