"""Per-session async command execution worker."""

from __future__ import annotations

import asyncio
import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db import queries


class SessionWorker:
    """Manages per-session command queues and sequential execution."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def submit(self, session_id: str, seq: int, container_ip: str) -> None:
        """Enqueue a command for execution."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
            self._tasks[session_id] = asyncio.create_task(self._worker_loop(session_id))
        self._queues[session_id].put_nowait((seq, container_ip))

    async def stop_session(self, session_id: str) -> None:
        """Stop the worker for a session."""
        if session_id in self._tasks:
            self._tasks[session_id].cancel()
            del self._tasks[session_id]
        self._queues.pop(session_id, None)

    async def stop_all(self) -> None:
        """Stop all workers."""
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        self._queues.clear()

    async def _worker_loop(self, session_id: str) -> None:
        """Process commands sequentially for a session."""
        queue = self._queues[session_id]
        while True:
            try:
                seq, container_ip = await queue.get()
                await self._execute(session_id, seq, container_ip)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log and continue — don't let one bad command kill the worker
                print(f"Worker error for session {session_id} seq {seq}: {e}")

    async def _execute(self, session_id: str, seq: int, container_ip: str) -> None:
        """Execute a single command inside the container via the sidecar agent."""
        async with self._session_factory() as db:
            event = await queries.get_event(db, session_id=session_id, seq=seq)
            if not event:
                return

            payload = event["payload"]
            cmd = payload.get("cmd", "")
            cwd = payload.get("cwd", "/workspace")
            timeout = payload.get("timeout_seconds", 300)
            env = payload.get("env")

            # Mark running
            await queries.complete_event(
                db,
                session_id=session_id,
                seq=seq,
                status="running",
                result={},
            )

            # Resolve sidecar URL
            if ":" in container_ip:
                sidecar_url = f"http://{container_ip}"
            else:
                sidecar_url = f"http://{container_ip}:2222"

            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=timeout + 5) as client:
                    resp = await client.post(
                        f"{sidecar_url}/exec",
                        json={
                            "cmd": cmd,
                            "cwd": cwd,
                            "timeout_seconds": timeout,
                            "env": env,
                        },
                    )
                    result_data = resp.json()
                    result_data["duration_ms"] = int((time.time() - start) * 1000)

                    await queries.complete_event(
                        db,
                        session_id=session_id,
                        seq=seq,
                        status="done",
                        result=result_data,
                    )
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                await queries.complete_event(
                    db,
                    session_id=session_id,
                    seq=seq,
                    status="error",
                    result={
                        "stdout": "",
                        "stderr": str(e),
                        "exit_code": -1,
                        "duration_ms": duration_ms,
                    },
                )
