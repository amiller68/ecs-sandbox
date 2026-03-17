"""
Minimal sidecar agent that runs inside each sandbox container.
Listens on port 2222 and exposes /exec, /fs, /git endpoints.
"""

import asyncio
import base64
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ecs-sandbox-agent")


class ExecRequest(BaseModel):
    cmd: str
    cwd: str = "/workspace"
    timeout_seconds: int = 300
    env: dict[str, str] | None = None


class ExecResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class WriteFileRequest(BaseModel):
    path: str
    content_b64: str


class DeleteFileRequest(BaseModel):
    path: str


@app.post("/exec")
async def exec_command(req: ExecRequest) -> ExecResult:
    """Execute a command in the sandbox."""
    env = {**os.environ, **(req.env or {})}
    start = asyncio.get_event_loop().time()

    try:
        proc = await asyncio.create_subprocess_shell(
            req.cmd,
            cwd=req.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=req.timeout_seconds
        )
        duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)

        return ExecResult(
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=proc.returncode or 0,
            duration_ms=duration_ms,
        )
    except asyncio.TimeoutError:
        duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        return ExecResult(
            stdout="",
            stderr=f"Command timed out after {req.timeout_seconds}s",
            exit_code=124,
            duration_ms=duration_ms,
        )


@app.get("/fs")
async def read_file(path: str):
    """Read a file."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {path}")
    if p.is_dir():
        raise HTTPException(400, f"Path is a directory: {path}")
    content = p.read_bytes()
    return {
        "path": str(p),
        "content_b64": base64.b64encode(content).decode(),
        "size": len(content),
    }


@app.post("/fs")
async def write_file(req: WriteFileRequest):
    """Write a file."""
    p = Path(req.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = base64.b64decode(req.content_b64)
    p.write_bytes(content)
    return {"path": str(p), "size": len(content)}


@app.delete("/fs")
async def delete_file(req: DeleteFileRequest):
    """Delete a file."""
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.path}")
    p.unlink()
    return {"deleted": str(p)}


@app.get("/fs/list")
async def list_files(path: str = "/workspace"):
    """List files in a directory."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"Directory not found: {path}")
    if not p.is_dir():
        raise HTTPException(400, f"Path is not a directory: {path}")
    entries = []
    for entry in sorted(p.iterdir()):
        entries.append(
            {
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            }
        )
    return {"path": str(p), "entries": entries}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2222)
