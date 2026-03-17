# ecs-sandbox Documentation

## Guides

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | System design, data flow, session lifecycle, SQLite schema |
| [API Reference](API.md) | Complete REST API with request/response examples |
| [Local Development](LOCAL_DEV.md) | Setting up and running the project locally |
| [Deployment](DEPLOYMENT.md) | ECS deployment via Terraform Cloud |
| [Patterns](PATTERNS.md) | Coding conventions, module organization, error handling |
| [Project Layout](PROJECT_LAYOUT.md) | Directory structure and entry points |
| [Contributing](CONTRIBUTING.md) | Workflow for adding features and submitting changes |
| [Success Criteria](SUCCESS_CRITERIA.md) | CI gate requirements |

## For AI Agents

If you are an AI agent working on this codebase:

1. **Read `CLAUDE.md`** at the repo root first — it has the quick-reference commands and conventions
2. **Use `make` targets** — never run `pytest`, `black`, `ruff` directly
3. **Check `docs/PATTERNS.md`** for code style before writing new modules
4. **Check `docs/SUCCESS_CRITERIA.md`** to know what CI will validate
5. **Session IDs are caller-supplied** — the sandbox never generates or lists them
