"""Cron job: reap stale sessions and clean up old events."""

import os
import time

import sqlalchemy
from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker
from taskiq import TaskiqDepends

from src.tasks.cron import cron

STALE_THRESHOLD_MINUTES = int(os.getenv("CLEANUP_STALE_THRESHOLD_MINUTES", "60"))
RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))


def _get_session_factory(request: Request = TaskiqDepends()) -> async_sessionmaker:
    from src.db.connection import get_session_factory

    return get_session_factory(request.app.state.engine)


@cron("*/10 * * * *", lock_ttl=300)
async def reap_stale_sessions(
    request: Request = TaskiqDepends(),
) -> dict:
    """Mark stale sessions and clean up their containers."""
    sf = _get_session_factory(request)
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - (STALE_THRESHOLD_MINUTES * 60 * 1000)

    async with sf() as db:
        # Mark stale
        result = await db.execute(
            sqlalchemy.text("""UPDATE sessions SET status = 'stale'
                WHERE status = 'active' AND last_active_at < :cutoff"""),
            {"cutoff": cutoff},
        )
        await db.commit()
        stale_count = result.rowcount

    return {"stale_marked": stale_count}


@cron("0 */6 * * *", lock_ttl=600)
async def prune_old_events(
    request: Request = TaskiqDepends(),
) -> dict:
    """Delete events for sessions destroyed more than RETENTION_DAYS ago."""
    sf = _get_session_factory(request)
    cutoff = int(time.time() * 1000) - (RETENTION_DAYS * 24 * 60 * 60 * 1000)

    async with sf() as db:
        result = await db.execute(
            sqlalchemy.text("""DELETE FROM events WHERE session_id IN (
                    SELECT id FROM sessions
                    WHERE status = 'destroyed' AND last_active_at < :cutoff
                )"""),
            {"cutoff": cutoff},
        )
        await db.commit()
        pruned = result.rowcount

    return {"events_pruned": pruned}
