"""Typed query helpers for sessions and events."""

import json
import time

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from src.types import (
    Event,
    EventKind,
    EventStatus,
    Session,
    SessionStatus,
)


def _row_to_session(row: dict) -> Session:
    """Convert a raw DB row to a Session."""
    meta = row.get("metadata", "{}")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    return Session(
        id=row["id"],
        status=SessionStatus(row["status"]),
        container_id=row.get("container_id"),
        container_ip=row.get("container_ip"),
        created_at=row.get("created_at", 0),
        last_active_at=row.get("last_active_at", 0),
        expires_at=row.get("expires_at"),
        workspace_path=row.get("workspace_path"),
        metadata=meta,
    )


def _row_to_event(row: dict) -> Event:
    """Convert a raw DB row to an Event."""
    payload = row.get("payload", "{}")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            payload = {}

    result = row.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            pass

    return Event(
        session_id=row["session_id"],
        seq=row["seq"],
        kind=EventKind(row["kind"]),
        status=EventStatus(row["status"]),
        payload=payload,
        result=result,
        submitted_at=row.get("submitted_at", 0),
        completed_at=row.get("completed_at"),
    )


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(
        sqlalchemy.text("SELECT * FROM sessions WHERE id = :id"),
        {"id": session_id},
    )
    row = result.mappings().first()
    return _row_to_session(dict(row)) if row else None


async def touch_session(db: AsyncSession, session_id: str, ttl_seconds: int = 1800):
    now = int(time.time() * 1000)
    await db.execute(
        sqlalchemy.text(
            """UPDATE sessions SET last_active_at = :now, expires_at = :expires
            WHERE id = :id AND status = :active"""
        ),
        {
            "id": session_id,
            "active": SessionStatus.ACTIVE.value,
            "now": now,
            "expires": now + ttl_seconds * 1000,
        },
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
    kind: EventKind,
    payload: dict,
) -> int:
    now = int(time.time() * 1000)
    await db.execute(
        sqlalchemy.text(
            """INSERT INTO events (session_id, seq, kind, status, payload, submitted_at)
            VALUES (:sid, :seq, :kind, :status, :payload, :now)"""
        ),
        {
            "sid": session_id,
            "seq": seq,
            "kind": kind.value,
            "status": EventStatus.PENDING.value,
            "payload": json.dumps(payload),
            "now": now,
        },
    )
    await db.commit()
    return seq


async def get_event(db: AsyncSession, session_id: str, seq: int) -> Event | None:
    result = await db.execute(
        sqlalchemy.text("SELECT * FROM events WHERE session_id = :sid AND seq = :seq"),
        {"sid": session_id, "seq": seq},
    )
    row = result.mappings().first()
    return _row_to_event(dict(row)) if row else None


async def list_events(
    db: AsyncSession, session_id: str, limit: int = 50, after_seq: int = 0
) -> list[Event]:
    result = await db.execute(
        sqlalchemy.text("""SELECT * FROM events WHERE session_id = :sid AND seq > :after
            ORDER BY seq ASC LIMIT :limit"""),
        {"sid": session_id, "after": after_seq, "limit": limit},
    )
    return [_row_to_event(dict(row)) for row in result.mappings().all()]
