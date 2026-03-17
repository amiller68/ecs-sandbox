"""Cleanup/reaper logic for stale sessions.

Can be run as:
- A cron job via TaskIQ scheduler
- A standalone script via ECS scheduled task
"""

import os
import time

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from src.types import SessionStatus

STALE_THRESHOLD_MINUTES = int(os.getenv("CLEANUP_STALE_THRESHOLD_MINUTES", "60"))
RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))


async def mark_stale_sessions(db: AsyncSession) -> int:
    """Mark sessions as stale if inactive past the threshold."""
    cutoff = int(time.time() * 1000) - (STALE_THRESHOLD_MINUTES * 60 * 1000)
    result = await db.execute(
        sqlalchemy.text("""UPDATE sessions SET status = :stale
            WHERE status = :active AND last_active_at < :cutoff"""),
        {
            "stale": SessionStatus.STALE.value,
            "active": SessionStatus.ACTIVE.value,
            "cutoff": cutoff,
        },
    )
    await db.commit()
    return result.rowcount  # type: ignore[attr-defined]


async def get_active_sessions(db: AsyncSession) -> list[dict]:
    """Get all active sessions with container IDs."""
    result = await db.execute(
        sqlalchemy.text("SELECT id, container_id FROM sessions WHERE status = :active"),
        {"active": SessionStatus.ACTIVE.value},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_stale_sessions(db: AsyncSession) -> list[dict]:
    """Get all stale sessions with container IDs."""
    result = await db.execute(
        sqlalchemy.text("SELECT id, container_id FROM sessions WHERE status = :stale"),
        {"stale": SessionStatus.STALE.value},
    )
    return [dict(row) for row in result.mappings().all()]


async def mark_destroyed(db: AsyncSession, session_id: str):
    """Mark a session as destroyed after cleanup."""
    await db.execute(
        sqlalchemy.text("UPDATE sessions SET status = :destroyed WHERE id = :id"),
        {"destroyed": SessionStatus.DESTROYED.value, "id": session_id},
    )
    await db.commit()


async def prune_old_events(db: AsyncSession) -> int:
    """Delete events for sessions destroyed more than RETENTION_DAYS ago."""
    cutoff = int(time.time() * 1000) - (RETENTION_DAYS * 24 * 60 * 60 * 1000)
    result = await db.execute(
        sqlalchemy.text("""DELETE FROM events WHERE session_id IN (
                SELECT id FROM sessions
                WHERE status = :destroyed AND last_active_at < :cutoff
            )"""),
        {"destroyed": SessionStatus.DESTROYED.value, "cutoff": cutoff},
    )
    await db.commit()
    return result.rowcount  # type: ignore[attr-defined]
