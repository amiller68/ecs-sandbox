# Coding Patterns

## Python Conventions

### Formatting & Linting

- **Formatter:** Black (default config)
- **Linter:** Ruff
- **Type checker:** ty
- **Always** use `make` targets or `uv run` — never run tools directly

### Module Organization

```
apps/ecs-sandbox/src/
├── main.py                  # App entry, startup, mount routers
├── config.py                # Pydantic Settings, env var loading
├── routers/                 # FastAPI routers (one per domain)
│   ├── sandbox.py           # Session CRUD + exec routes
│   ├── fs.py                # Filesystem operations
│   └── git.py               # Git operations
├── services/                # Business logic
│   ├── session.py           # Session lifecycle, TTL refresh
│   ├── docker_manager.py    # Container create/exec/destroy
│   ├── worker.py            # Async queue + per-session executor
│   └── cleanup.py           # Reaper logic
├── middleware/
│   └── auth.py              # X-Sandbox-Secret check
├── db/
│   ├── connection.py        # aiosqlite setup, pragma application
│   ├── migrations/          # Plain SQL migration files
│   └── queries.py           # Typed query helpers
└── storage/
    ├── efs.py
    └── s3.py
```

### Naming

- **Files and modules:** `snake_case`
- **Classes:** `PascalCase`
- **Functions and variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Pydantic models:** `PascalCase` with descriptive suffixes (`CreateSessionRequest`, `ExecResult`)

### Error Handling

Use `HTTPException` for API errors with consistent error bodies:

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail={"error": "session_not_found", "detail": f"No active session with id {session_id}"}
)
```

### Async Patterns

- All database access via `aiosqlite` (async)
- Per-session `asyncio.Lock` for mutating operations (container start/stop)
- Per-session `asyncio.Queue` for command dispatch
- Use `asyncio.TaskGroup` for structured concurrency where appropriate

### Configuration

Use Pydantic Settings for environment variable loading:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    sandbox_secret: str
    sandbox_image: str = "ecs-sandbox-agent:latest"
    db_path: str = "/data/ecs-sandbox.db"
    max_containers: int = 50
    default_ttl_seconds: int = 1800
```

### Testing

- **Framework:** pytest + pytest-asyncio
- **Location:** `tests/` directory at the app level
- **Fixtures:** Use `conftest.py` for shared fixtures
- **Async tests:** Use `@pytest.mark.asyncio` decorator
- **No mocks for SQLite** — use an in-memory database for tests

```python
@pytest.fixture
async def db():
    """In-memory SQLite for tests."""
    async with aiosqlite.connect(":memory:") as conn:
        await apply_migrations(conn)
        yield conn
```

### Dependencies

- Pin major versions in `pyproject.toml`: `"fastapi>=0.115,<1"`
- Use `uv` workspace for internal dependencies: `ecs-sandbox-client = { workspace = true }`

## Background Jobs

### Taskiq Pattern

```python
from taskiq import InMemoryBroker
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker

broker = ListQueueBroker(url="redis://localhost:6379")

@broker.task
async def cleanup_stale_sessions():
    """Reap sessions past their TTL."""
    ...
```

### Scheduler

Cron tasks are defined in the scheduler module and triggered via Taskiq's scheduler:

```python
from taskiq import TaskiqScheduler

scheduler = TaskiqScheduler(broker=broker, sources=[...])
```

## Git Conventions

### Commit Format

Conventional Commits:

```
<type>(<scope>): <summary>

feat(api): add sync exec mode with 30s timeout
fix(cleanup): handle orphan containers without session rows
docs: add deployment guide
chore(iac): update ECS task definition memory limits
```

### Types

- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `chore` — tooling, CI, dependencies
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding or updating tests
