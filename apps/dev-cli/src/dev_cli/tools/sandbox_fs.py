"""Filesystem tools — read, write, list files in the sandbox."""

from __future__ import annotations

import base64

from pydantic_ai import RunContext

from dev_cli.agent.deps import AgentDeps
from ecs_sandbox import FileWriteRequest


async def sandbox_read_file(
    ctx: RunContext[AgentDeps],
    path: str,
) -> str:
    """Read a file from the sandbox filesystem.

    Args:
        path: Absolute path inside the sandbox (e.g. /workspace/main.py).
    """
    try:
        content = await ctx.deps.sandbox.read_file(ctx.deps.session_id, path)
        return content
    except Exception as e:
        return f"Error reading {path}: {e}"


async def sandbox_write_file(
    ctx: RunContext[AgentDeps],
    path: str,
    content: str,
) -> str:
    """Write content to a file in the sandbox filesystem.

    Args:
        path: Absolute path inside the sandbox (e.g. /workspace/script.py).
        content: Text content to write.
    """
    try:
        content_b64 = base64.b64encode(content.encode()).decode()
        await ctx.deps.sandbox.write_file(
            ctx.deps.session_id,
            FileWriteRequest(path=path, content_b64=content_b64),
        )
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


async def sandbox_list_files(
    ctx: RunContext[AgentDeps],
    path: str = "/workspace",
) -> str:
    """List files and directories in a sandbox path.

    Args:
        path: Directory path to list (default: /workspace).
    """
    try:
        entries = await ctx.deps.sandbox.list_files(ctx.deps.session_id, path)
        if not entries:
            return f"{path} is empty"
        lines = []
        for e in entries:
            prefix = "d" if e.is_dir else "f"
            size = f" ({e.size}b)" if e.size is not None else ""
            lines.append(f"  [{prefix}] {e.name}{size}")
        return f"Contents of {path}:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listing {path}: {e}"
