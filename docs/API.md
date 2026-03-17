# API Reference

All endpoints require the `X-Sandbox-Secret: <secret>` header.

Base URL: `http://localhost:8000` (local) or your deployed service URL.

---

## Sessions

### Create Session

```
POST /sandbox
```

**Request:**

```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "ttl_seconds": 1800,
  "image": "ecs-sandbox-agent:latest",
  "metadata": {}
}
```

- `id` — caller-supplied UUID (required)
- `ttl_seconds` — idle timeout before session becomes stale (default: 1800)
- `image` — Docker image for the sandbox container (default: configured `SANDBOX_IMAGE`)
- `metadata` — arbitrary JSON stored with the session

**Response:** `201 Created`

```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "active",
  "created_at": 1710000000000,
  "expires_at": 1710001800000
}
```

**Errors:**
- `409 Conflict` — session ID already exists and is active
- `503 Service Unavailable` — container ceiling reached (`MAX_CONTAINERS`)

### Destroy Session

```
DELETE /sandbox/{id}
```

Stops the container, marks the session `destroyed`, optionally archives workspace to S3.

**Response:** `200 OK`

**Errors:**
- `404 Not Found` — session does not exist or already destroyed

---

## Command Execution

### Submit Command (non-blocking)

```
POST /sandbox/{id}/exec
```

**Request:**

```json
{
  "cmd": "python run_analysis.py --input data.csv",
  "cwd": "/workspace",
  "timeout_seconds": 300,
  "env": { "MY_VAR": "value" },
  "sync": false
}
```

- `cmd` — shell command to execute (required)
- `cwd` — working directory inside the container (default: `/workspace`)
- `timeout_seconds` — max execution time (default: 300)
- `env` — additional environment variables
- `sync` — if `true`, block until complete (capped at 30s)

**Response (async):** `202 Accepted`

```json
{
  "seq": 7,
  "status": "pending"
}
```

**Response (sync):** `200 OK`

```json
{
  "seq": 7,
  "status": "done",
  "result": {
    "stdout": "1 1 2 3 5 8 13 ...\n",
    "stderr": "",
    "exit_code": 0,
    "duration_ms": 245
  }
}
```

### Get Event Result

```
GET /sandbox/{id}/events/{seq}
```

**Response (still running):** `202 Accepted`

```json
{
  "seq": 7,
  "status": "running"
}
```

**Response (complete):** `200 OK`

```json
{
  "seq": 7,
  "status": "done",
  "kind": "exec_submit",
  "payload": { "cmd": "python run_analysis.py --input data.csv" },
  "result": {
    "stdout": "...",
    "stderr": "",
    "exit_code": 0,
    "duration_ms": 245
  },
  "submitted_at": 1710000060000,
  "completed_at": 1710000060245
}
```

### Get Session History

```
GET /sandbox/{id}/history?limit=50&after_seq=0
```

Returns all events for the session, ordered by `seq`. Paginated.

- `limit` — max events to return (default: 50)
- `after_seq` — return events after this sequence number (default: 0)

**Response:** `200 OK`

```json
{
  "events": [
    {
      "seq": 1,
      "kind": "exec_submit",
      "status": "done",
      "payload": { "cmd": "echo hello" },
      "result": { "stdout": "hello\n", "stderr": "", "exit_code": 0, "duration_ms": 12 },
      "submitted_at": 1710000000000,
      "completed_at": 1710000000012
    }
  ],
  "has_more": false
}
```

---

## Filesystem Operations

All fs operations are **synchronous** and refresh the session TTL.

### Read File

```
GET /sandbox/{id}/fs?path=/workspace/output.csv
```

**Response:** `200 OK`

```json
{
  "path": "/workspace/output.csv",
  "content_b64": "aGVsbG8gd29ybGQ=",
  "size_bytes": 11
}
```

### Write File

```
POST /sandbox/{id}/fs
```

```json
{
  "path": "/workspace/script.py",
  "content_b64": "cHJpbnQoImhlbGxvIik="
}
```

**Response:** `201 Created`

### Delete File

```
DELETE /sandbox/{id}/fs
```

```json
{
  "path": "/workspace/script.py"
}
```

**Response:** `200 OK`

### List Directory

```
GET /sandbox/{id}/fs/list?path=/workspace
```

**Response:** `200 OK`

```json
{
  "path": "/workspace",
  "entries": [
    { "name": "script.py", "type": "file", "size_bytes": 18 },
    { "name": "data", "type": "directory" }
  ]
}
```

---

## Git Operations

Git ops are submitted as **async events** (same pattern as exec) since operations like clone can be slow.

### Clone Repository

```
POST /sandbox/{id}/git/clone
```

```json
{
  "url": "https://github.com/owner/repo.git",
  "dest": "/workspace/repo"
}
```

**Response:** `202 Accepted`

```json
{ "seq": 3, "status": "pending" }
```

### Commit Changes

```
POST /sandbox/{id}/git/commit
```

```json
{
  "message": "Add analysis results",
  "files": ["output.csv", "report.md"]
}
```

**Response:** `202 Accepted`

```json
{ "seq": 4, "status": "pending" }
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "session_not_found",
  "detail": "No active session with id 6ba7b810-..."
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid input) |
| 401 | Missing or invalid `X-Sandbox-Secret` |
| 404 | Session or event not found |
| 409 | Session ID already exists |
| 408 | Sync exec timed out (30s cap) |
| 503 | Container ceiling reached |
