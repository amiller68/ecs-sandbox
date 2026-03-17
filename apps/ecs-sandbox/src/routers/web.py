"""Web terminal: browser-based shell for sandbox sessions."""

import asyncio
import json
import pathlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.db import queries
from src.db.connection import get_session_factory
from src.services import session as session_svc

router = APIRouter(prefix="/web", tags=["web"])

_static_dir = pathlib.Path(__file__).resolve().parent.parent / "static"


@router.get("", response_class=HTMLResponse)
async def web_terminal():
    """Serve the terminal UI."""
    html = (_static_dir / "index.html").read_text()
    return HTMLResponse(html)


@router.websocket("/ws/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    """WebSocket terminal for a sandbox session."""
    token = websocket.query_params.get("token", "")
    config = websocket.app.state.config

    if token != config.sandbox_secret:
        await websocket.close(code=4001, reason="invalid token")
        return

    await websocket.accept()

    engine = websocket.app.state.engine
    sf = get_session_factory(engine)

    # Auto-create session if it doesn't exist, or replay history if it does
    docker = websocket.app.state.docker
    try:
        async with sf() as db:
            session = await queries.get_session(db, session_id=session_id)

        if session and session["status"] == "active":
            async with sf() as db:
                events = await queries.list_events(db, session_id=session_id, limit=100)
            await websocket.send_json(
                {"type": "history", "events": _serialize_events(events)}
            )
        elif session and session["status"] != "active":
            await websocket.send_json(
                {"type": "error", "message": f"session is {session['status']}"}
            )
            await websocket.close()
            return
        else:
            # No session exists — create one automatically
            async with sf() as db:
                await session_svc.create_session(
                    db, docker, config, session_id=session_id
                )
            await websocket.send_json({"type": "session_created", "id": session_id})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

    # Message loop
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if "type" in msg and msg["type"] == "create_session":
                await _handle_create_session(websocket, sf, session_id)
            elif "cmd" in msg:
                await _handle_exec(websocket, sf, session_id, msg["cmd"])
            else:
                await websocket.send_json(
                    {"type": "error", "message": "unknown message"}
                )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _handle_create_session(websocket: WebSocket, sf, session_id: str):
    config = websocket.app.state.config
    docker = websocket.app.state.docker

    try:
        async with sf() as db:
            await session_svc.create_session(db, docker, config, session_id=session_id)
        await websocket.send_json({"type": "session_created", "id": session_id})
    except session_svc.SessionConflictError:
        await websocket.send_json(
            {"type": "error", "message": "session already exists"}
        )
    except session_svc.SessionCapacityError:
        await websocket.send_json(
            {"type": "error", "message": "max containers reached"}
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


async def _handle_exec(websocket: WebSocket, sf, session_id: str, cmd: str):
    config = websocket.app.state.config
    worker = websocket.app.state.worker

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session["status"] != "active":
            await websocket.send_json(
                {"type": "error", "message": "session not found or not active"}
            )
            return

        seq = await queries.next_seq(db, session_id=session_id)
        await queries.insert_event(
            db,
            session_id=session_id,
            seq=seq,
            kind="exec_submit",
            payload={"cmd": cmd, "cwd": "/workspace"},
        )
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    worker.submit(session_id, seq, session["container_ip"])

    # Poll for result
    for _ in range(1500):  # 5 min max (1500 * 0.2s)
        await asyncio.sleep(0.2)
        async with sf() as db:
            event = await queries.get_event(db, session_id=session_id, seq=seq)
        if event and event["status"] in ("done", "error"):
            result = event.get("result")
            if isinstance(result, str):
                result = json.loads(result)
            await websocket.send_json(
                {
                    "type": "output",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exit_code": result.get("exit_code", 1),
                    "duration_ms": result.get("duration_ms", 0),
                }
            )
            return

    await websocket.send_json({"type": "error", "message": "command timed out"})


def _serialize_events(events: list[dict]) -> list[dict]:
    """Ensure event payloads/results are JSON-serializable dicts."""
    out = []
    for e in events:
        e = dict(e)
        for field in ("payload", "result"):
            if isinstance(e.get(field), str):
                try:
                    e[field] = json.loads(e[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        out.append(e)
    return out
