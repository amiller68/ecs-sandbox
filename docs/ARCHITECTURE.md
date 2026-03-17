# Architecture

## Overview

ecs-sandbox is a long-running HTTP service that manages ephemeral Docker containers on behalf of AI agents. Each sandbox is an isolated environment with its own filesystem, process tree, and session history.

```
Caller (agent / app)
  └── POST /sandbox/{id}/exec
  └── GET  /sandbox/{id}/history
  └── POST /sandbox
  └── DELETE /sandbox/{id}

ecs-sandbox (FastAPI, ECS Fargate)
  ├── Docker daemon (runc runtime)
  │    └── per-session containers (sandbox-agent sidecar on :2222)
  └── SQLite (WAL mode, on EFS)
       └── sessions table
       └── events table

EFS volume
  └── /data/ecs-sandbox.db
  └── /data/workspaces/{session_id}/

S3 (optional)
  └── post-session workspace archival
```

## Components

### Control Plane (`apps/ecs-sandbox`)

FastAPI service that:
- Manages session lifecycle (create, destroy, TTL refresh)
- Dispatches commands to sandbox containers via per-session async queues
- Records all events (commands, results, fs ops) in SQLite
- Runs a cleanup job that reaps stale sessions and orphan containers

### Sandbox Agent (`apps/ecs-sandbox-agent`)

Minimal FastAPI sidecar baked into each sandbox container. Listens on port 2222. Accepts exec, fs, and git commands from the control plane. This is the process that actually runs user commands inside the isolated environment.

### Client Library (`packages/ecs-sandbox-client`)

Typed Python client for callers. Wraps the REST API in a `SandboxClient` class with Pydantic models for all request/response types.

### Dev CLI (`apps/dev-cli`)

A simple agent built with pydantic-ai and the Anthropic API. Uses the client library to interact with a running sandbox. For development and testing only — demonstrates how an agent uses the sandbox as a tool.

## Session Lifecycle

```
create → active → [idle TTL expires] → stale → [cleanup job] → destroyed
                → [activity refreshes TTL]  → active (loop)
                → [explicit DELETE]         → destroyed
```

- Session IDs are **caller-supplied UUIDs**
- Sessions are **not enumerable** — no list endpoint
- Every successful interaction updates `last_active_at`, refreshing the TTL
- Default TTL: 30 minutes of inactivity

## Command Execution

Commands are non-blocking by default:

```
POST /sandbox/{id}/exec
  → INSERT event (status=pending)
  → enqueue to per-session asyncio.Queue
  → return 202 with seq number

Worker coroutine (per session):
  dequeue event
  → POST http://{container_ip}:2222/exec
  → stream stdout/stderr
  → UPDATE event SET result=..., status='done'
```

Commands within a session execute **sequentially** in submission order. This preserves coherent shell state and avoids filesystem races.

A `sync: true` flag is available for short commands where the caller wants to block (capped at 30s).

## State: SQLite

SQLite is the state backend. It lives on an EFS volume mounted to the ECS task.

### Why SQLite

- No extra infrastructure (no Postgres, no Redis for state)
- Hundreds of concurrent reads, serialized writes — sufficient for a single ECS task
- WAL mode allows readers and a single writer to operate without blocking each other
- Migration path to Postgres is straightforward (swap SQLAlchemy connection string)

### Schema

```sql
-- Sessions
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,        -- caller-supplied UUID
    status          TEXT NOT NULL DEFAULT 'active',  -- active | stale | destroyed
    container_id    TEXT,
    container_ip    TEXT,
    created_at      INTEGER NOT NULL,        -- unix ms
    last_active_at  INTEGER NOT NULL,        -- unix ms
    expires_at      INTEGER,                 -- unix ms
    workspace_path  TEXT,
    metadata        TEXT                     -- JSON blob
);

-- Events (session history)
CREATE TABLE events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    seq             INTEGER NOT NULL,        -- monotonic per session
    kind            TEXT NOT NULL,            -- exec_submit | exec_result | fs_write | ...
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | running | done | error
    payload         TEXT NOT NULL,            -- JSON
    result          TEXT,                     -- JSON (stdout/stderr/exit_code/duration_ms)
    submitted_at    INTEGER NOT NULL,
    completed_at    INTEGER,
    UNIQUE(session_id, seq)
);
```

### Pragmas

Applied on every connection open:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

## Storage Backends

| Backend | Mechanism | Use case |
|---------|-----------|----------|
| **None** | tmpfs inside container | Fully ephemeral |
| **EFS** | Bind-mount at `/workspace` | Survives container restart (recommended default) |
| **S3** | Sync on session destroy | Durable archival |

EFS is recommended since it also hosts the SQLite file.

## Concurrency & Locking

- **Database:** SQLite WAL mode handles read/write concurrency
- **Session operations:** Per-session `asyncio.Lock` prevents concurrent container start/stop
- **Container ceiling:** `MAX_CONTAINERS` counter; returns 503 when full (autoscaling signal)

Since ecs-sandbox runs as a single ECS task, in-process locks are sufficient.

## Cleanup Job

Runs as a scheduled ECS task via EventBridge cron. Same Docker image, same EFS volume.

1. Mark stale sessions (`last_active_at` past threshold)
2. Stop and remove stale containers
3. Archive workspaces to S3 (optional)
4. Mark sessions destroyed
5. Prune old events past retention window
6. Sweep orphan Docker containers

## Infrastructure

- **ECS Fargate** — runs the control plane, worker, and scheduler
- **EFS** — hosts SQLite database and workspace directories
- **ECR** — container registry for service images
- **EventBridge** — triggers the cleanup cron
- **S3** — optional workspace archival
- **ALB** — load balancer with HTTPS termination

All infrastructure is defined in `iac/` and managed via Terraform Cloud.
