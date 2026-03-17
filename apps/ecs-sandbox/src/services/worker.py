"""Per-session asyncio queue and executor for command execution."""

import asyncio
import json
import time

import httpx
import sqlalchemy
from sqlalchemy.ext.asyncio import async_sessionmaker


class SessionWorker:
    """Manages per-session command execution queues."""

    def __init__(self, session_factory: async_sessionmaker):
        self._sf = session_factory
        self._tasks: dict[str, asyncio.Task] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def submit(self, session_id: str, seq: int, container_ip: str):
        """Submit a command for async execution."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
            self._tasks[session_id] = asyncio.create_task(self._worker(session_id))
        self._queues[session_id].put_nowait((seq, container_ip))

    async def _worker(self, session_id: str):
        """Process commands sequentially for a session."""
        queue = self._queues[session_id]
        while True:
            seq, container_ip = await queue.get()
            try:
                await self._process(session_id, seq, container_ip)
            except Exception as e:
                print(f"Error processing seq {seq} for {session_id}: {e}")
            finally:
                queue.task_done()

    async def _process(self, session_id: str, seq: int, container_ip: str):
        """Execute a command via the sidecar agent."""
        async with self._sf() as db:
            # Get event payload
            result = await db.execute(
                sqlalchemy.text(
                    "SELECT payload FROM events WHERE session_id = :sid AND seq = :seq"
                ),
                {"sid": session_id, "seq": seq},
            )
            row = result.first()
            if not row:
                return

            payload = (
                json.loads(row.payload) if isinstance(row.payload, str) else row.payload
            )

            # Update status to running
            await db.execute(
                sqlalchemy.text(
                    "UPDATE events SET status = 'running' WHERE session_id = :sid AND seq = :seq"
                ),
                {"sid": session_id, "seq": seq},
            )
            await db.commit()

        # Execute via sidecar
        url = (
            f"http://{container_ip}:2222"
            if ":" not in container_ip
            else f"http://{container_ip}"
        )
        try:
            async with httpx.AsyncClient(
                timeout=payload.get("timeout_seconds", 300)
            ) as client:
                resp = await client.post(f"{url}/exec", json=payload)
                exec_result = resp.json()
        except Exception as e:
            exec_result = {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "duration_ms": 0,
            }

        # Write result back
        now = int(time.time() * 1000)
        async with self._sf() as db:
            await db.execute(
                sqlalchemy.text(
                    """UPDATE events SET status = :status, result = :result, completed_at = :now
                    WHERE session_id = :sid AND seq = :seq"""
                ),
                {
                    "status": (
                        "done" if exec_result.get("exit_code", 1) == 0 else "error"
                    ),
                    "result": json.dumps(exec_result),
                    "now": now,
                    "sid": session_id,
                    "seq": seq,
                },
            )
            await db.commit()

    async def stop_session(self, session_id: str):
        """Stop the worker for a session."""
        if session_id in self._tasks:
            self._tasks[session_id].cancel()
            del self._tasks[session_id]
        self._queues.pop(session_id, None)

    async def stop_all(self):
        """Stop all session workers."""
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        self._queues.clear()
