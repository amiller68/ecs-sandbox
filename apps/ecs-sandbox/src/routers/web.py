"""Web terminal: browser-based shell for sandbox sessions."""

import asyncio
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.db import queries
from src.routers._deps import context_from_request
from src.services.session import (
    CreateParams,
    SessionCapacityError,
    SessionConflictError,
    create_session,
)
from src.types import (
    EventKind,
    EventStatus,
    SessionStatus,
    WsError,
    WsHistory,
    WsOutput,
    WsSessionCreated,
)

router = APIRouter(prefix="/web", tags=["web"])


@router.get("", response_class=HTMLResponse)
async def web_terminal():
    """Serve the terminal UI."""
    import pathlib

    static_dir = pathlib.Path(__file__).resolve().parent.parent / "static"
    html = (static_dir / "index.html").read_text()
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

    sf = websocket.app.state.session_factory

    # Auto-create session if it doesn't exist, or replay history if it does
    try:
        async with sf() as db:
            session = await queries.get_session(db, session_id=session_id)

        if session and session.status == SessionStatus.ACTIVE:
            async with sf() as db:
                events = await queries.list_events(db, session_id=session_id, limit=100)
            msg = WsHistory(events=[asdict(e) for e in events])
            await websocket.send_json(msg.to_msg())
        elif session and session.status != SessionStatus.ACTIVE:
            msg = WsError(message=f"session is {session.status.value}")
            await websocket.send_json(msg.to_msg())
            await websocket.close()
            return
        else:
            async with sf() as db:
                ctx = context_from_request(websocket, db)
                params = CreateParams(session_id=session_id)
                await create_session(params, ctx)
            await websocket.send_json(WsSessionCreated(id=session_id).to_msg())
    except Exception as e:
        await websocket.send_json(WsError(message=str(e)).to_msg())

    # Message loop
    try:
        while True:
            raw = await websocket.receive_text()
            import json

            msg_data = json.loads(raw)

            if msg_data.get("type") == "create_session":
                await _handle_create_session(websocket, sf, session_id)
            elif "cmd" in msg_data:
                await _handle_exec(websocket, sf, session_id, msg_data["cmd"])
            else:
                await websocket.send_json(WsError(message="unknown message").to_msg())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(WsError(message=str(e)).to_msg())
        except Exception:
            pass


async def _handle_create_session(websocket: WebSocket, sf, session_id: str):
    try:
        async with sf() as db:
            ctx = context_from_request(websocket, db)
            params = CreateParams(session_id=session_id)
            await create_session(params, ctx)
        await websocket.send_json(WsSessionCreated(id=session_id).to_msg())
    except SessionConflictError:
        await websocket.send_json(WsError(message="session already exists").to_msg())
    except SessionCapacityError:
        await websocket.send_json(WsError(message="max containers reached").to_msg())
    except Exception as e:
        await websocket.send_json(WsError(message=str(e)).to_msg())


async def _handle_exec(websocket: WebSocket, sf, session_id: str, cmd: str):
    config = websocket.app.state.config
    worker = websocket.app.state.worker

    async with sf() as db:
        session = await queries.get_session(db, session_id=session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            await websocket.send_json(
                WsError(message="session not found or not active").to_msg()
            )
            return

        seq = await queries.next_seq(db, session_id=session_id)
        await queries.insert_event(
            db,
            session_id=session_id,
            seq=seq,
            kind=EventKind.EXEC_SUBMIT,
            payload={"cmd": cmd, "cwd": "/workspace"},
        )
        await queries.touch_session(
            db, session_id=session_id, ttl_seconds=config.default_ttl_seconds
        )

    worker.submit(session_id, seq, session.container_ip)

    # Poll for result
    for _ in range(1500):  # 5 min max (1500 * 0.2s)
        await asyncio.sleep(0.2)
        async with sf() as db:
            event = await queries.get_event(db, session_id=session_id, seq=seq)
        if event and event.status in (EventStatus.DONE, EventStatus.ERROR):
            result = event.result or {}
            msg = WsOutput(
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                exit_code=result.get("exit_code", 1),
                duration_ms=result.get("duration_ms", 0),
            )
            await websocket.send_json(msg.to_msg())
            return

    await websocket.send_json(WsError(message="command timed out").to_msg())
