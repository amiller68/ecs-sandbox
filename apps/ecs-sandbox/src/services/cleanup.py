"""Cleanup / reaper logic — runs as a separate ECS scheduled task or locally."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import Config
from src.db import queries
from src.services.docker_manager import DockerManager


async def run_cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    docker: DockerManager,
    config: Config,
) -> dict:
    """Run the full cleanup cycle. Returns stats."""
    stats = {"stale_marked": 0, "reaped": 0, "orphans_stopped": 0, "events_pruned": 0}

    async with session_factory() as db:
        # 1. Mark stale sessions
        stale_threshold_ms = config.CLEANUP_STALE_THRESHOLD_MINUTES * 60 * 1000
        stale_sessions = await queries.list_stale_sessions(
            db, stale_threshold_ms=stale_threshold_ms
        )
        for session in stale_sessions:
            await db.execute(
                text("UPDATE sessions SET status = 'stale' WHERE id = :id"),
                {"id": session["id"]},
            )
            stats["stale_marked"] += 1
        await db.commit()

        # 2. Reap stale containers
        result = await db.execute(
            text(
                "SELECT * FROM sessions WHERE status = 'stale' AND container_id IS NOT NULL"
            )
        )
        for row in result.mappings().all():
            try:
                await docker.stop_container(row["container_id"])
            except Exception:
                pass
            await db.execute(
                text(
                    "UPDATE sessions SET status = 'destroyed', container_id = NULL WHERE id = :id"
                ),
                {"id": row["id"]},
            )
            stats["reaped"] += 1
        await db.commit()

        # 3. Prune old events
        retention_ms = config.CLEANUP_RETENTION_DAYS * 24 * 60 * 60 * 1000
        cutoff = int(time.time() * 1000) - retention_ms
        prune_result = await db.execute(
            text(
                "DELETE FROM events WHERE session_id IN "
                "(SELECT id FROM sessions WHERE status = 'destroyed' AND last_active_at < :cutoff)"
            ),
            {"cutoff": cutoff},
        )
        stats["events_pruned"] = prune_result.rowcount
        await db.commit()

    # 4. Orphan sweep
    try:
        containers = await docker.list_sandbox_containers()
        async with session_factory() as db:
            for c in containers:
                sid = c["session_id"]
                if not sid:
                    continue
                session = await queries.get_session(db, session_id=sid)
                if not session or session["status"] != "active":
                    await docker.stop_container(c["container_id"])
                    stats["orphans_stopped"] += 1
    except Exception:
        pass

    return stats


async def cleanup_entrypoint() -> None:
    """Entry point for running cleanup as a standalone task."""
    from src.config import Config
    from src.db.connection import get_engine, get_session_factory

    config = Config()
    engine = get_engine(config.db_path)
    session_factory = get_session_factory(engine)
    docker = DockerManager(config)
    await docker.connect()

    try:
        stats = await run_cleanup(session_factory, docker, config)
        print(f"Cleanup complete: {stats}")
    finally:
        await docker.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_entrypoint())
