"""Session lifecycle management."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Config
from src.db import queries
from src.services.docker_manager import DockerManager

# Per-session locks to prevent concurrent container operations
_session_locks: dict[str, asyncio.Lock] = {}

# Active container counter
_active_containers: int = 0


def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def create_session(
    db: AsyncSession,
    docker: DockerManager,
    config: Config,
    *,
    session_id: str,
    ttl_seconds: int | None = None,
    image: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new sandbox session with a container."""
    global _active_containers

    if _active_containers >= config.max_containers:
        raise SessionCapacityError("max containers reached")

    ttl = ttl_seconds or config.default_ttl_seconds
    image = image or config.sandbox_image

    # Determine workspace path
    workspace_path = None
    if config.workspace_backend == "efs":
        workspace_path = os.path.join(config.efs_workspace_root, session_id)

    async with get_session_lock(session_id):
        # Check for existing active session
        existing = await queries.get_session(db, session_id=session_id)
        if existing and existing["status"] == "active":
            raise SessionConflictError(f"session {session_id} already active")

        # Create DB record
        session = await queries.create_session(
            db,
            session_id=session_id,
            ttl_seconds=ttl,
            workspace_path=workspace_path,
            metadata=metadata,
        )

        # Start container
        container_id, container_ip = await docker.create_container(
            session_id, image=image, workspace_path=workspace_path
        )
        await queries.update_session_container(
            db,
            session_id=session_id,
            container_id=container_id,
            container_ip=container_ip,
        )
        _active_containers += 1

        session["container_id"] = container_id
        session["container_ip"] = container_ip

    return session


async def destroy_session(
    db: AsyncSession,
    docker: DockerManager,
    *,
    session_id: str,
) -> None:
    """Stop container and mark session destroyed."""
    global _active_containers

    async with get_session_lock(session_id):
        session = await queries.get_session(db, session_id=session_id)
        if not session:
            return

        if session.get("container_id"):
            await docker.stop_container(session["container_id"])
            _active_containers = max(0, _active_containers - 1)

        await queries.destroy_session(db, session_id=session_id)

    # Clean up lock
    _session_locks.pop(session_id, None)


def get_active_count() -> int:
    return _active_containers


class SessionCapacityError(Exception):
    pass


class SessionConflictError(Exception):
    pass
