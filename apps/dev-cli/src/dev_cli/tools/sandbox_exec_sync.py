"""Synchronous command execution — blocks until result is available."""

from __future__ import annotations

import asyncio

from pydantic_ai import RunContext

from dev_cli.agent.deps import AgentDeps


async def sandbox_exec_sync(
    ctx: RunContext[AgentDeps],
    cmd: str,
    cwd: str = "/workspace",
    timeout_seconds: int = 30,
) -> str:
    """Execute a short command in the sandbox and wait for the result.

    Best for quick commands that complete in under 30 seconds:
    ls, cat, echo, pip install, python scripts, etc.

    Args:
        cmd: Shell command to execute.
        cwd: Working directory inside the sandbox.
        timeout_seconds: Max wait time (capped at 30s).
    """
    timeout_seconds = min(timeout_seconds, 30)
    resp = await ctx.deps.sandbox.exec(
        ctx.deps.session_id,
        cmd=cmd,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        sync=True,
    )

    # Poll for completion
    for _ in range(timeout_seconds * 2):
        event = await ctx.deps.sandbox.get_event(ctx.deps.session_id, resp.seq)
        if event.status in ("done", "error"):
            result = event.result if isinstance(event.result, dict) else {}
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)
            duration = result.get("duration_ms", 0)

            parts = []
            if stdout:
                parts.append(f"stdout:\n{stdout}")
            if stderr:
                parts.append(f"stderr:\n{stderr}")
            parts.append(f"exit_code={exit_code} ({duration}ms)")
            return "\n".join(parts)

        await asyncio.sleep(0.5)

    return f"Command timed out after {timeout_seconds}s. seq={resp.seq}, check history later."
