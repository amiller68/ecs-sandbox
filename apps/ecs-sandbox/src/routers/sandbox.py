"""Session CRUD and exec routes."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.db import queries
from src.routers._deps import context_from_request
from src.services.session import (
    CreateParams,
    SessionCapacityError,
    SessionConflictError,
    create_session,
    destroy_session,
)
from src.types import EventKind, SessionStatus

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class CreateSessionBody(BaseModel):
    id: str
    ttl_seconds: int = 1800
    image: str | None = None
    metadata: dict | None = None


class ExecBody(BaseModel):
    cmd: str
    cwd: str = "/workspace"
    timeout_seconds: int = 300
    env: dict[str, str] | None = None
    sync: bool = False


@router.post("", status_code=201)
async def create_session_route(body: CreateSessionBody, request: Request):
    """Create a new sandbox session."""
    sf = request.app.state.session_factory

    async with sf() as db:
        ctx = context_from_request(request, db)
        try:
            params = CreateParams(
                session_id=body.id,
                ttl_seconds=body.ttl_seconds,
                image=body.image,
                metadata=body.metadata,
            )
            session = await create_session(params, ctx)
            return asdict(session)
        except SessionCapacityError:
            raise HTTPException(503, "max containers reached")
        except SessionConflictError:
            raise HTTPException(409, f"session {body.id} already active")


@router.post("/{session_id}/exec", status_code=202)
async def submit_exec(session_id: str, body: ExecBody, request: Request):
    """Submit a command for execution."""
    sf = request.app.state.session_factory
    config = request.app.state.config
    worker = request.app.state.worker

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise HTTPException(404, "session not found or not active")

        seq = await queries.next_seq(db, session_id=session_id)
        await queries.insert_event(
            db,
            session_id=session_id,
            seq=seq,
            kind=EventKind.EXEC_SUBMIT,
            payload={
                "cmd": body.cmd,
                "cwd": body.cwd,
                "timeout_seconds": body.timeout_seconds,
                "env": body.env,
            },
        )
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    worker.submit(session_id, seq, session.container_ip)
    return {"seq": seq, "status": "pending"}


@router.get("/{session_id}/events/{seq}")
async def get_event(session_id: str, seq: int, request: Request):
    """Get a specific event result."""
    sf = request.app.state.session_factory

    async with sf() as db:
        event = await queries.get_event(db, session_id=session_id, seq=seq)
        if not event:
            raise HTTPException(404, "event not found")
        return asdict(event)


@router.get("/{session_id}/history")
async def get_history(
    session_id: str,
    request: Request,
    limit: int = 50,
    after_seq: int = 0,
):
    """Get session history."""
    sf = request.app.state.session_factory

    async with sf() as db:
        events = await queries.list_events(
            db, session_id=session_id, limit=limit, after_seq=after_seq
        )
        return [asdict(e) for e in events]


@router.delete("/{session_id}")
async def destroy_session_route(session_id: str, request: Request):
    """Destroy a sandbox session."""
    sf = request.app.state.session_factory

    async with sf() as db:
        ctx = context_from_request(request, db)
        return await destroy_session(session_id, ctx)
