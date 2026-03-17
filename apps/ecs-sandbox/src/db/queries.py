"""Typed query helpers for sessions and events."""

import json
import time

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession


async def create_session(
    db: AsyncSession,
    session_id: str,
    ttl_seconds: int = 1800,
    metadata: dict | None = None,
) -> dict:
    now = int(time.time() * 1000)
    await db.execute(
        sqlalchemy.text(
            """INSERT INTO sessions (id, status, created_at, last_active_at, expires_at, metadata)
            VALUES (:id, 'active', :now, :now, :expires, :metadata)"""
        ),
        {
            "id": session_id,
            "now": now,
            "expires": now + ttl_seconds * 1000,
            "metadata": json.dumps(metadata or {}),
        },
    )
    await db.commit()
    return {"id": session_id, "status": "active", "created_at": now}


async def get_session(db: AsyncSession, session_id: str) -> dict | None:
    result = await db.execute(
        sqlalchemy.text("SELECT * FROM sessions WHERE id = :id"),
        {"id": session_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def touch_session(db: AsyncSession, session_id: str, ttl_seconds: int = 1800):
    now = int(time.time() * 1000)
    await db.execute(
        sqlalchemy.text(
            """UPDATE sessions SET last_active_at = :now, expires_at = :expires
            WHERE id = :id AND status = 'active'"""
        ),
        {"id": session_id, "now": now, "expires": now + ttl_seconds * 1000},
    )
    await db.commit()


async def next_seq(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        sqlalchemy.text(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM events WHERE session_id = :sid"
        ),
        {"sid": session_id},
    )
    return result.scalar()


async def insert_event(
    db: AsyncSession,
    session_id: str,
    seq: int,
    kind: str,
    payload: dict,
) -> int:
    now = int(time.time() * 1000)
    await db.execute(
        sqlalchemy.text(
            """INSERT INTO events (session_id, seq, kind, status, payload, submitted_at)
            VALUES (:sid, :seq, :kind, 'pending', :payload, :now)"""
        ),
        {
            "sid": session_id,
            "seq": seq,
            "kind": kind,
            "payload": json.dumps(payload),
            "now": now,
        },
    )
    await db.commit()
    return seq


async def get_event(db: AsyncSession, session_id: str, seq: int) -> dict | None:
    result = await db.execute(
        sqlalchemy.text("SELECT * FROM events WHERE session_id = :sid AND seq = :seq"),
        {"sid": session_id, "seq": seq},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_events(
    db: AsyncSession, session_id: str, limit: int = 50, after_seq: int = 0
) -> list[dict]:
    result = await db.execute(
        sqlalchemy.text("""SELECT * FROM events WHERE session_id = :sid AND seq > :after
            ORDER BY seq ASC LIMIT :limit"""),
        {"sid": session_id, "after": after_seq, "limit": limit},
    )
    return [dict(row) for row in result.mappings().all()]
