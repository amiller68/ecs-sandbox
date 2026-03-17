"""Async command execution tool — fire-and-forget, check history for results."""

from __future__ import annotations

from pydantic_ai import RunContext

from dev_cli.agent.deps import AgentDeps


async def sandbox_exec(
    ctx: RunContext[AgentDeps],
    cmd: str,
    cwd: str = "/workspace",
    timeout_seconds: int = 300,
) -> str:
    """Execute a command in the sandbox asynchronously (non-blocking).

    Use this for long-running commands. Returns a sequence number you can
    check later via the session history. For quick commands, prefer
    sandbox_exec_sync instead.

    Args:
        cmd: Shell command to execute.
        cwd: Working directory inside the sandbox.
        timeout_seconds: Max execution time.
    """
    resp = await ctx.deps.sandbox.exec(
        ctx.deps.session_id,
        cmd=cmd,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )
    return f"Command submitted. seq={resp.seq}, status={resp.status}. Use sandbox history to check results."
