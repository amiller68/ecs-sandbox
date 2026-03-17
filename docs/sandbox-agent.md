# Sandbox Agent (Sidecar)

The sandbox agent is a minimal FastAPI service baked into each sandbox container. It listens on port 2222 and executes commands on behalf of the control plane.

## How It Works

When the control plane creates a session, it starts a Docker container from the `ecs-sandbox-agent` image. That container runs the agent process, which exposes three capabilities:

1. **Exec** — run shell commands inside the container
2. **Filesystem** — read, write, delete, and list files
3. **Git** — clone repositories and commit changes

The control plane never executes commands directly in the container. Instead, it sends HTTP requests to the agent sidecar at `http://{container_ip}:2222`.

## Container Image

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY agent.py /agent.py
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

EXPOSE 2222
CMD ["python", "/agent.py"]
```

The image is intentionally minimal:
- Python 3.12 runtime for executing Python code
- Git and curl for common agent operations
- `/workspace` as the default working directory

## Endpoints

### Execute Command

```
POST /exec
```

```json
{
  "cmd": "python script.py",
  "cwd": "/workspace",
  "timeout_seconds": 300,
  "env": { "KEY": "value" }
}
```

Runs the command via `subprocess`, captures stdout/stderr, and returns:

```json
{
  "stdout": "output here\n",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 245
}
```

### Read File

```
GET /fs?path=/workspace/output.csv
```

Returns base64-encoded file content.

### Write File

```
POST /fs
```

```json
{
  "path": "/workspace/script.py",
  "content_b64": "cHJpbnQoImhlbGxvIik="
}
```

### Delete File

```
DELETE /fs
```

### List Directory

```
GET /fs/list?path=/workspace
```

### Git Clone

```
POST /git/clone
```

```json
{ "url": "https://github.com/owner/repo.git", "dest": "/workspace/repo" }
```

### Git Commit

```
POST /git/commit
```

```json
{ "message": "Add results", "files": ["output.csv"] }
```

## Security

Each sandbox container runs with:

- **Memory limit:** `SANDBOX_MEMORY_LIMIT` (default: 512m)
- **CPU limit:** `SANDBOX_CPU_LIMIT` (default: 0.5)
- **Network:** `SANDBOX_NETWORK` (default: none — no external network access)
- **PID limit:** `SANDBOX_PIDS_LIMIT` (default: 128)

The `network=none` default means sandbox containers cannot reach the internet or other containers. The control plane communicates with the sidecar via the Docker bridge network.

## Customization

To add tools or languages to the sandbox environment, modify the `apps/ecs-sandbox-agent/Dockerfile`:

```dockerfile
# Add Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Add additional Python packages
RUN pip install numpy pandas matplotlib
```

Rebuild and push the image, then update `SANDBOX_IMAGE` in the service configuration.
