"""Session lifecycle — functional operations with explicit context."""

import json
import time
from dataclasses import dataclass

import sqlalchemy

from src.services._context import Context
from src.types import Session, SessionStatus


class SessionCapacityError(Exception):
    pass


class SessionConflictError(Exception):
    pass


@dataclass
class CreateParams:
    session_id: str
    ttl_seconds: int = 1800
    image: str | None = None
    metadata: dict | None = None


async def create_session(params: CreateParams, ctx: Context) -> Session:
    """Create a new sandbox session with container."""
    # Check for existing active session
    result = await ctx.db.execute(
        sqlalchemy.text("SELECT id FROM sessions WHERE id = :id AND status = :active"),
        {"id": params.session_id, "active": SessionStatus.ACTIVE.value},
    )
    if result.first():
        raise SessionConflictError(f"session {params.session_id} already active")

    # Check capacity
    active = await ctx.db.execute(
        sqlalchemy.text("SELECT COUNT(*) FROM sessions WHERE status = :active"),
        {"active": SessionStatus.ACTIVE.value},
    )
    if active.scalar() >= ctx.config.max_containers:
        raise SessionCapacityError("max containers reached")

    now = int(time.time() * 1000)
    image = params.image or ctx.config.sandbox_image

    container_info = await ctx.docker.create_container(
        session_id=params.session_id,
        image=image,
        memory_limit=ctx.config.sandbox_memory_limit,
        cpu_limit=ctx.config.sandbox_cpu_limit,
        pids_limit=ctx.config.sandbox_pids_limit,
    )

    expires = now + params.ttl_seconds * 1000
    try:
        await ctx.db.execute(
            sqlalchemy.text(
                """INSERT INTO sessions (id, status, container_id, container_ip,
                   created_at, last_active_at, expires_at, metadata)
                   VALUES (:id, :status, :cid, :cip, :now, :now, :expires, :meta)"""
            ),
            {
                "id": params.session_id,
                "status": SessionStatus.ACTIVE.value,
                "cid": container_info["container_id"],
                "cip": container_info["container_ip"],
                "now": now,
                "expires": expires,
                "meta": json.dumps(params.metadata or {}),
            },
        )
        await ctx.db.commit()
    except Exception:
        # Clean up orphaned container if DB insert fails
        await ctx.docker.remove_container(container_info["container_id"])
        raise

    return Session(
        id=params.session_id,
        status=SessionStatus.ACTIVE,
        container_id=container_info["container_id"],
        container_ip=container_info["container_ip"],
        created_at=now,
        last_active_at=now,
        expires_at=expires,
    )


async def destroy_session(session_id: str, ctx: Context) -> dict:
    """Stop container and mark session destroyed."""
    result = await ctx.db.execute(
        sqlalchemy.text("SELECT container_id FROM sessions WHERE id = :id"),
        {"id": session_id},
    )
    row = result.first()
    if row and row.container_id:
        await ctx.docker.remove_container(row.container_id)

    await ctx.db.execute(
        sqlalchemy.text("UPDATE sessions SET status = :status WHERE id = :id"),
        {"status": SessionStatus.DESTROYED.value, "id": session_id},
    )
    await ctx.db.commit()

    await ctx.worker.stop_session(session_id)
    return {"status": "destroyed"}
