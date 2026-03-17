"""Typed query helpers for sessions and events."""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# --- Sessions ---


async def create_session(
    db: AsyncSession,
    *,
    session_id: str,
    ttl_seconds: int,
    container_id: str | None = None,
    container_ip: str | None = None,
    workspace_path: str | None = None,
    metadata: dict | None = None,
) -> dict:
    now = int(time.time() * 1000)
    expires_at = now + (ttl_seconds * 1000)
    meta_json = json.dumps(metadata) if metadata else None

    await db.execute(
        text(
            "INSERT INTO sessions (id, status, container_id, container_ip, "
            "created_at, last_active_at, expires_at, workspace_path, metadata) "
            "VALUES (:id, 'active', :container_id, :container_ip, "
            ":created_at, :last_active_at, :expires_at, :workspace_path, :metadata)"
        ),
        {
            "id": session_id,
            "container_id": container_id,
            "container_ip": container_ip,
            "created_at": now,
            "last_active_at": now,
            "expires_at": expires_at,
            "workspace_path": workspace_path,
            "metadata": meta_json,
        },
    )
    await db.commit()
    return await get_session(db, session_id=session_id)


async def get_session(db: AsyncSession, *, session_id: str) -> dict | None:
    result = await db.execute(
        text("SELECT * FROM sessions WHERE id = :id"), {"id": session_id}
    )
    row = result.mappings().first()
    if not row:
        return None
    return _session_row_to_dict(row)


async def update_session_container(
    db: AsyncSession,
    *,
    session_id: str,
    container_id: str,
    container_ip: str,
) -> None:
    await db.execute(
        text(
            "UPDATE sessions SET container_id = :cid, container_ip = :cip "
            "WHERE id = :id"
        ),
        {"id": session_id, "cid": container_id, "cip": container_ip},
    )
    await db.commit()


async def touch_session(db: AsyncSession, *, session_id: str, ttl_seconds: int) -> None:
    now = int(time.time() * 1000)
    expires_at = now + (ttl_seconds * 1000)
    await db.execute(
        text(
            "UPDATE sessions SET last_active_at = :now, expires_at = :exp WHERE id = :id"
        ),
        {"id": session_id, "now": now, "exp": expires_at},
    )
    await db.commit()


async def destroy_session(db: AsyncSession, *, session_id: str) -> None:
    await db.execute(
        text("UPDATE sessions SET status = 'destroyed' WHERE id = :id"),
        {"id": session_id},
    )
    await db.commit()


async def list_stale_sessions(
    db: AsyncSession, *, stale_threshold_ms: int
) -> list[dict]:
    cutoff = int(time.time() * 1000) - stale_threshold_ms
    result = await db.execute(
        text(
            "SELECT * FROM sessions WHERE status = 'active' AND last_active_at < :cutoff"
        ),
        {"cutoff": cutoff},
    )
    return [_session_row_to_dict(r) for r in result.mappings().all()]


# --- Events ---


async def next_seq(db: AsyncSession, *, session_id: str) -> int:
    result = await db.execute(
        text(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM events WHERE session_id = :sid"
        ),
        {"sid": session_id},
    )
    return result.scalar_one()


async def insert_event(
    db: AsyncSession,
    *,
    session_id: str,
    seq: int,
    kind: str,
    payload: dict,
) -> dict:
    now = int(time.time() * 1000)
    await db.execute(
        text(
            "INSERT INTO events (session_id, seq, kind, status, payload, submitted_at) "
            "VALUES (:sid, :seq, :kind, 'pending', :payload, :submitted_at)"
        ),
        {
            "sid": session_id,
            "seq": seq,
            "kind": kind,
            "payload": json.dumps(payload),
            "submitted_at": now,
        },
    )
    await db.commit()
    return {"session_id": session_id, "seq": seq, "status": "pending"}


async def complete_event(
    db: AsyncSession,
    *,
    session_id: str,
    seq: int,
    status: str,
    result: dict,
) -> None:
    now = int(time.time() * 1000)
    await db.execute(
        text(
            "UPDATE events SET status = :status, result = :result, completed_at = :now "
            "WHERE session_id = :sid AND seq = :seq"
        ),
        {
            "sid": session_id,
            "seq": seq,
            "status": status,
            "result": json.dumps(result),
            "now": now,
        },
    )
    await db.commit()


async def get_event(db: AsyncSession, *, session_id: str, seq: int) -> dict | None:
    result = await db.execute(
        text("SELECT * FROM events WHERE session_id = :sid AND seq = :seq"),
        {"sid": session_id, "seq": seq},
    )
    row = result.mappings().first()
    if not row:
        return None
    return _event_row_to_dict(row)


async def list_events(
    db: AsyncSession,
    *,
    session_id: str,
    limit: int = 50,
    after_seq: int = 0,
) -> list[dict]:
    result = await db.execute(
        text(
            "SELECT * FROM events WHERE session_id = :sid AND seq > :after "
            "ORDER BY seq ASC LIMIT :limit"
        ),
        {"sid": session_id, "after": after_seq, "limit": limit},
    )
    return [_event_row_to_dict(r) for r in result.mappings().all()]


# --- Helpers ---


def _session_row_to_dict(row: Any) -> dict:
    d = dict(row)
    if d.get("metadata"):
        d["metadata"] = json.loads(d["metadata"])
    return d


def _event_row_to_dict(row: Any) -> dict:
    d = dict(row)
    if d.get("payload") and isinstance(d["payload"], str):
        d["payload"] = json.loads(d["payload"])
    if d.get("result") and isinstance(d["result"], str):
        d["result"] = json.loads(d["result"])
    return d
