"""Filesystem operations routes — synchronous proxy to sidecar agent."""

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.db import queries
from src.types import SessionStatus

router = APIRouter(prefix="/sandbox/{session_id}/fs", tags=["filesystem"])


class WriteFileBody(BaseModel):
    path: str
    content_b64: str


class DeleteFileBody(BaseModel):
    path: str


async def _get_sidecar_url(request: Request, session_id: str) -> str:
    sf = request.app.state.session_factory
    config = request.app.state.config

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise HTTPException(404, "session not found or not active")
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    ip = session.container_ip
    if ":" in ip:
        return f"http://{ip}"
    return f"http://{ip}:2222"


@router.get("")
async def read_file(session_id: str, path: str, request: Request):
    """Read a file from the sandbox."""
    url = await _get_sidecar_url(request, session_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{url}/fs", params={"path": path})
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()


@router.post("")
async def write_file(session_id: str, body: WriteFileBody, request: Request):
    """Write a file to the sandbox."""
    url = await _get_sidecar_url(request, session_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{url}/fs", json=body.model_dump())
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()


@router.delete("")
async def delete_file(session_id: str, body: DeleteFileBody, request: Request):
    """Delete a file from the sandbox."""
    url = await _get_sidecar_url(request, session_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request("DELETE", f"{url}/fs", json=body.model_dump())
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()


@router.get("/list")
async def list_files(session_id: str, request: Request, path: str = "/workspace"):
    """List files in the sandbox."""
    url = await _get_sidecar_url(request, session_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{url}/fs/list", params={"path": path})
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()
