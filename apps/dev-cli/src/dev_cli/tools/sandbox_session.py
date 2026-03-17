"""Session info and history tools."""

from __future__ import annotations

from pydantic_ai import RunContext

from dev_cli.agent.deps import AgentDeps


async def sandbox_session_info(
    ctx: RunContext[AgentDeps],
    limit: int = 20,
    after_seq: int = 0,
) -> str:
    """Get recent session history — shows commands and their results.

    Use this to check on async commands or review what has happened.

    Args:
        limit: Max number of events to return.
        after_seq: Only return events after this sequence number.
    """
    try:
        events = await ctx.deps.sandbox.get_history(
            ctx.deps.session_id, limit=limit, after_seq=after_seq
        )
        if not events:
            return "No events in session history."

        lines = []
        for ev in events:
            result_summary = ""
            if ev.result and isinstance(ev.result, dict):
                exit_code = ev.result.get("exit_code", "?")
                stdout = ev.result.get("stdout", "")
                if stdout and len(stdout) > 200:
                    stdout = stdout[:200] + "..."
                result_summary = f" → exit={exit_code}"
                if stdout:
                    result_summary += f"\n    {stdout}"

            cmd = (
                ev.payload.get("cmd", ev.kind)
                if isinstance(ev.payload, dict)
                else ev.kind
            )
            lines.append(f"  [{ev.seq}] {ev.status}: {cmd}{result_summary}")

        return "Session history:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error fetching history: {e}"
