"""Cron job: reap stale sessions and clean up old events."""

import os
import time

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from src.tasks.cron import cron
from src.tasks.deps import get_db_session
from src.types import SessionStatus

STALE_THRESHOLD_MINUTES = int(os.getenv("CLEANUP_STALE_THRESHOLD_MINUTES", "60"))
RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))


@cron("*/10 * * * *", lock_ttl=300)
async def reap_stale_sessions(
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict:
    """Mark stale sessions and clean up their containers."""
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - (STALE_THRESHOLD_MINUTES * 60 * 1000)

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
    return {"stale_marked": result.rowcount}  # type: ignore[union-attr]


@cron("0 */6 * * *", lock_ttl=600)
async def prune_old_events(
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict:
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
    return {"events_pruned": result.rowcount}  # type: ignore[union-attr]
