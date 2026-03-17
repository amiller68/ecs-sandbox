# Pre-fill token from URL query param

**Status:** Planned
**Labels:** web-terminal, dx, auto

## Objective

Allow the sandbox secret to be passed via URL query parameter so developers can bookmark a direct link like `http://localhost:8000/web?token=not-secure` and skip the form field.

## Implementation

1. In `apps/ecs-sandbox/src/static/terminal.js`, on page load parse `URLSearchParams` for `token`
2. If present, pre-fill the token input field
3. Optionally auto-connect if both token and session ID are provided via URL

## Files

- `apps/ecs-sandbox/src/static/terminal.js` — Parse URL params on load
- `apps/ecs-sandbox/src/static/index.html` — No changes needed

## Acceptance Criteria

- [ ] `http://localhost:8000/web?token=not-secure` pre-fills the token field
- [ ] `http://localhost:8000/web?token=not-secure&session=abc` auto-connects
- [ ] Manual entry still works when no params provided

## Verification

Open `http://localhost:8000/web?token=not-secure` — token field is filled, just click Connect.
