"""Minimal sidecar agent — runs inside each sandbox container on port 2222.

Exposes /exec, /fs, /fs/list endpoints for the control plane to proxy into.
"""

from __future__ import annotations

import asyncio
import base64
import os
import shutil
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ecs-sandbox-agent", version="0.1.0")


# --- Models ---


class ExecRequest(BaseModel):
    cmd: str
    cwd: str = "/workspace"
    timeout_seconds: int = 300
    env: dict[str, str] | None = None


class ExecResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


class WriteFileRequest(BaseModel):
    path: str
    content_b64: str


class DeleteFileRequest(BaseModel):
    path: str


# --- Exec ---


@app.post("/exec")
async def exec_command(req: ExecRequest):
    """Execute a shell command and return stdout/stderr/exit_code."""
    env = os.environ.copy()
    if req.env:
        env.update(req.env)

    try:
        proc = await asyncio.create_subprocess_shell(
            req.cmd,
            cwd=req.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=req.timeout_seconds
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ExecResult(
                stdout="",
                stderr=f"Command timed out after {req.timeout_seconds}s",
                exit_code=-1,
            )

        return ExecResult(
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            exit_code=proc.returncode or 0,
        )
    except Exception as e:
        return ExecResult(stdout="", stderr=str(e), exit_code=-1)


# --- Filesystem ---


@app.get("/fs")
async def read_file(path: str):
    """Read a file and return its content."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"{path} not found")
    if not p.is_file():
        raise HTTPException(400, f"{path} is not a file")

    try:
        content = p.read_text(errors="replace")
        return {"path": path, "content": content, "size": p.stat().st_size}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/fs")
async def write_file(req: WriteFileRequest):
    """Write base64-encoded content to a file."""
    p = Path(req.path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        content = base64.b64decode(req.content_b64)
        p.write_bytes(content)
        return {"path": req.path, "size": len(content)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/fs")
async def delete_file(req: DeleteFileRequest):
    """Delete a file or directory."""
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(404, f"{req.path} not found")

    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"deleted": req.path}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/fs/list")
async def list_files(path: str = "/workspace"):
    """List directory contents."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"{path} not found")
    if not p.is_dir():
        raise HTTPException(400, f"{path} is not a directory")

    entries = []
    for child in sorted(p.iterdir()):
        stat = child.stat()
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size": stat.st_size if child.is_file() else None,
            }
        )
    return entries


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=2222)


if __name__ == "__main__":
    main()
