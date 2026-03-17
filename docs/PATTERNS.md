# Coding Patterns

## Error Handling

Use `HTTPException` for API errors with consistent error bodies:

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail={"error": "session_not_found", "detail": f"No active session with id {session_id}"}
)
```

Custom exception classes for domain errors (e.g. `SessionConflictError`, `SessionCapacityError`) are raised by services and caught by routers to map to HTTP status codes.

## Module Organization

```
apps/ecs-sandbox/src/
├── server.py                # App factory, lifespan, router mounting
├── config.py                # Pydantic-style config, env var loading
├── __main__.py              # Entry point (uvicorn runner)
├── routers/                 # FastAPI routers (one per domain)
│   ├── _deps.py             # context_from_request() — builds Context from Request
│   ├── sandbox.py           # Session CRUD + exec routes
│   ├── fs.py                # Filesystem operations (proxied to sidecar)
│   ├── git.py               # Git operations (async via worker)
│   └── web.py               # Browser terminal (HTML + WebSocket)
├── services/                # Business logic
│   ├── _context.py          # Context dataclass (db, docker, config, worker)
│   ├── session.py           # Session lifecycle (create, destroy, TTL refresh)
│   ├── docker_manager.py    # Container create/exec/destroy via Docker SDK
│   ├── worker.py            # Per-session asyncio queue + executor
│   └── cleanup.py           # Reaper logic
├── middleware/
│   └── auth.py              # X-Sandbox-Secret validation
├── db/
│   ├── connection.py        # SQLAlchemy async engine setup
│   ├── migrations/          # Plain SQL migration files
│   └── queries.py           # Typed query helpers
├── storage/
│   ├── efs.py               # EFS workspace backend
│   └── s3.py                # S3 workspace backend
├── tasks/                   # Background jobs (Taskiq)
│   ├── __init__.py          # Broker initialization
│   ├── cron.py              # @cron decorator with Redis distributed locking
│   ├── scheduler.py         # TaskiqScheduler setup
│   ├── deps.py              # Taskiq dependency injection (db, redis)
│   └── jobs/
│       └── cleanup.py       # Cron jobs: reap_stale_sessions, prune_old_events
└── static/                  # Web terminal UI assets
```

### Dependency Injection

Routers use `context_from_request()` to build a `Context` dataclass from the FastAPI `Request`:

```python
from src.routers._deps import context_from_request

@router.post("/sandbox")
async def create(body: CreateSessionBody, request: Request, db: AsyncSession = Depends(get_db)):
    ctx = context_from_request(request, db)
    return await create_session(CreateParams(...), ctx)
```

Services accept `(params, ctx: Context)` — parameters first, context second.

## Naming Conventions

- **Files and modules:** `snake_case`
- **Classes:** `PascalCase`
- **Functions and variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Pydantic models:** `PascalCase` with descriptive suffixes (`CreateSessionBody`, `ExecBody`, `WriteFileBody`)
- **Internal modules:** Prefixed with `_` (`_deps.py`, `_context.py`)

## Output Conventions

- **API responses:** JSON with consistent structure
- **Error responses:** `{"error": "error_code", "detail": "human-readable message"}`
- **Async operations:** Return `202 Accepted` with event/sequence tracking
- **Logging:** Standard Python logging via uvicorn

## Testing Patterns

- **Framework:** pytest + pytest-asyncio
- **Location:** `tests/` directory at the app level
- **Fixtures:** Use `conftest.py` for shared fixtures
- **Async tests:** Use `@pytest.mark.asyncio` decorator
- **No mocks for SQLite** — use an in-memory database

```python
@pytest.fixture
async def db():
    """In-memory SQLite for tests."""
    async with aiosqlite.connect(":memory:") as conn:
        await apply_migrations(conn)
        yield conn
```

## Common Idioms

### Async Patterns

- All database access via SQLAlchemy async sessions
- Per-session `asyncio.Lock` for mutating operations (container start/stop)
- Per-session `asyncio.Queue` for command dispatch via `SessionWorker`
- Use `asyncio.TaskGroup` for structured concurrency where appropriate

### Background Jobs

Cron tasks use the `@cron` decorator with Redis distributed locking:

```python
@cron("*/10 * * * *", lock_ttl=300)
async def reap_stale_sessions() -> dict:
    """Reap sessions past their TTL."""
    ...
```

### Configuration

Environment variables loaded via a `Config` dataclass in `config.py`. Key settings: `sandbox_secret`, `sandbox_image`, `db_path`, `redis_url`, `max_containers`, `default_ttl_seconds`.

## Git Conventions

### Commit Format

Conventional Commits: `<type>(<scope>): <summary>`

```
feat(api): add sync exec mode with 30s timeout
fix(cleanup): handle orphan containers without session rows
docs: add deployment guide
chore(iac): update ECS task definition memory limits
```

### Types

`feat`, `fix`, `docs`, `chore`, `refactor`, `test`

### Scopes

`api`, `cli`, `client`, `agent`, `iac`, `cleanup`, `worker`, `web`
