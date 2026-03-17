"""Typed Python client for the ecs-sandbox API."""

import time

import httpx

from ecs_sandbox.models import (
    CreateSessionRequest,
    Event,
    ExecRequest,
    ExecSubmitResponse,
    Session,
)


class SandboxClient:
    """Client for interacting with the ecs-sandbox API."""

    def __init__(self, base_url: str, secret: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-Sandbox-Secret": secret}
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self._timeout,
        )

    async def create_session(
        self,
        session_id: str,
        ttl_seconds: int = 1800,
        image: str | None = None,
        metadata: dict | None = None,
    ) -> Session:
        req = CreateSessionRequest(
            id=session_id,
            ttl_seconds=ttl_seconds,
            image=image,
            metadata=metadata,
        )
        async with self._client() as client:
            resp = await client.post("/sandbox", json=req.model_dump(exclude_none=True))
            resp.raise_for_status()
            return Session(**resp.json())

    async def exec(
        self,
        session_id: str,
        cmd: str,
        cwd: str = "/workspace",
        timeout_seconds: int = 300,
        env: dict[str, str] | None = None,
        sync: bool = False,
    ) -> ExecSubmitResponse:
        req = ExecRequest(
            cmd=cmd,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            env=env,
            sync=sync,
        )
        async with self._client() as client:
            resp = await client.post(
                f"/sandbox/{session_id}/exec",
                json=req.model_dump(exclude_none=True),
            )
            resp.raise_for_status()
            return ExecSubmitResponse(**resp.json())

    async def get_event(self, session_id: str, seq: int) -> Event:
        async with self._client() as client:
            resp = await client.get(f"/sandbox/{session_id}/events/{seq}")
            resp.raise_for_status()
            return Event(**resp.json())

    async def get_history(
        self, session_id: str, limit: int = 50, after_seq: int = 0
    ) -> list[Event]:
        async with self._client() as client:
            resp = await client.get(
                f"/sandbox/{session_id}/history",
                params={"limit": limit, "after_seq": after_seq},
            )
            resp.raise_for_status()
            return [Event(**e) for e in resp.json()]

    async def wait_for_event(
        self,
        session_id: str,
        seq: int,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> Event:
        """Poll until an event is complete."""
        import asyncio

        start = time.time()
        while time.time() - start < timeout:
            event = await self.get_event(session_id, seq)
            if event.status in ("done", "error"):
                return event
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Event {seq} did not complete within {timeout}s")

    async def destroy_session(self, session_id: str) -> dict:
        async with self._client() as client:
            resp = await client.delete(f"/sandbox/{session_id}")
            resp.raise_for_status()
            return resp.json()

    async def read_file(self, session_id: str, path: str) -> dict:
        async with self._client() as client:
            resp = await client.get(
                f"/sandbox/{session_id}/fs", params={"path": path}
            )
            resp.raise_for_status()
            return resp.json()

    async def write_file(
        self, session_id: str, path: str, content_b64: str
    ) -> dict:
        async with self._client() as client:
            resp = await client.post(
                f"/sandbox/{session_id}/fs",
                json={"path": path, "content_b64": content_b64},
            )
            resp.raise_for_status()
            return resp.json()

    async def list_files(
        self, session_id: str, path: str = "/workspace"
    ) -> dict:
        async with self._client() as client:
            resp = await client.get(
                f"/sandbox/{session_id}/fs/list", params={"path": path}
            )
            resp.raise_for_status()
            return resp.json()
