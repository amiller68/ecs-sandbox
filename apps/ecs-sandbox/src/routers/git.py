"""Git operations routes — async, dispatched as events."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.db import queries
from src.types import EventKind, SessionStatus

router = APIRouter(prefix="/sandbox/{session_id}/git", tags=["git"])


class GitCloneBody(BaseModel):
    url: str
    dest: str = "/workspace"


class GitCommitBody(BaseModel):
    message: str
    files: list[str] = []


@router.post("/clone", status_code=202)
async def git_clone(session_id: str, body: GitCloneBody, request: Request):
    """Clone a repository into the sandbox."""
    sf = request.app.state.session_factory
    config = request.app.state.config
    worker = request.app.state.worker

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise HTTPException(404, "session not found or not active")

        seq = await queries.next_seq(db, session_id=session_id)
        cmd = f"git clone {body.url} {body.dest}"
        await queries.insert_event(
            db,
            session_id=session_id,
            seq=seq,
            kind=EventKind.GIT_CLONE,
            payload={
                "cmd": cmd,
                "cwd": "/",
                "timeout_seconds": 300,
                "url": body.url,
                "dest": body.dest,
            },
        )
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    worker.submit(session_id, seq, session.container_ip)
    return {"seq": seq, "status": "pending"}


@router.post("/commit", status_code=202)
async def git_commit(session_id: str, body: GitCommitBody, request: Request):
    """Commit changes in the sandbox."""
    sf = request.app.state.session_factory
    config = request.app.state.config
    worker = request.app.state.worker

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise HTTPException(404, "session not found or not active")

        seq = await queries.next_seq(db, session_id=session_id)
        files_arg = " ".join(body.files) if body.files else "."
        cmd = f"cd /workspace && git add {files_arg} && git commit -m '{body.message}'"
        await queries.insert_event(
            db,
            session_id=session_id,
            seq=seq,
            kind=EventKind.GIT_COMMIT,
            payload={"cmd": cmd, "cwd": "/workspace", "timeout_seconds": 60},
        )
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    worker.submit(session_id, seq, session.container_ip)
    return {"seq": seq, "status": "pending"}
