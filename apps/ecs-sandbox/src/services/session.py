"""Session lifecycle management and TTL refresh."""

import asyncio
import os
import time

import sqlalchemy

_session_locks: dict[str, asyncio.Lock] = {}
_active_containers: int = 0
MAX_CONTAINERS: int = int(os.environ.get("MAX_CONTAINERS", "50"))


class SessionCapacityError(Exception):
    pass


class SessionConflictError(Exception):
    pass


def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


def get_active_container_count() -> int:
    return _active_containers


def increment_containers():
    global _active_containers
    _active_containers += 1


def decrement_containers():
    global _active_containers
    _active_containers = max(0, _active_containers - 1)


def remove_session_lock(session_id: str):
    _session_locks.pop(session_id, None)


async def create_session(
    db, docker, config, session_id, ttl_seconds=1800, image=None, metadata=None
):
    """Create a new sandbox session with container."""
    global _active_containers

    if _active_containers >= MAX_CONTAINERS:
        raise SessionCapacityError("max containers reached")

    # Check for existing active session
    result = await db.execute(
        sqlalchemy.text("SELECT id FROM sessions WHERE id = :id AND status = 'active'"),
        {"id": session_id},
    )
    if result.first():
        raise SessionConflictError(f"session {session_id} already active")

    now = int(time.time() * 1000)
    img = image or config.sandbox_image

    # Start container
    lock = get_session_lock(session_id)
    async with lock:
        container_info = await docker.create_container(
            session_id=session_id,
            image=img,
            memory_limit=config.sandbox_memory_limit,
            cpu_limit=config.sandbox_cpu_limit,
            pids_limit=config.sandbox_pids_limit,
        )

        await db.execute(
            sqlalchemy.text(
                """INSERT INTO sessions (id, status, container_id, container_ip,
                   created_at, last_active_at, expires_at, metadata)
                   VALUES (:id, 'active', :cid, :cip, :now, :now, :expires, :meta)"""
            ),
            {
                "id": session_id,
                "cid": container_info["container_id"],
                "cip": container_info["container_ip"],
                "now": now,
                "expires": now + ttl_seconds * 1000,
                "meta": __import__("json").dumps(metadata or {}),
            },
        )
        await db.commit()
        _active_containers += 1

    return {
        "id": session_id,
        "status": "active",
        "container_id": container_info["container_id"],
        "container_ip": container_info["container_ip"],
        "created_at": now,
        "last_active_at": now,
        "expires_at": now + ttl_seconds * 1000,
    }


async def destroy_session(db, docker, session_id):
    """Stop container and mark session destroyed."""
    global _active_containers

    lock = get_session_lock(session_id)
    async with lock:
        result = await db.execute(
            sqlalchemy.text("SELECT container_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
        row = result.first()
        if row and row.container_id:
            await docker.remove_container(row.container_id)

        await db.execute(
            sqlalchemy.text("UPDATE sessions SET status = 'destroyed' WHERE id = :id"),
            {"id": session_id},
        )
        await db.commit()
        _active_containers = max(0, _active_containers - 1)

    remove_session_lock(session_id)
