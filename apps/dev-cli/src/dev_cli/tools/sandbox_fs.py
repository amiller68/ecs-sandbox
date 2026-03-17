"""Filesystem tools — read, write, list files in the sandbox."""

from __future__ import annotations

import base64

from pydantic_ai import RunContext

from dev_cli.agent.deps import AgentDeps


async def sandbox_read_file(
    ctx: RunContext[AgentDeps],
    path: str,
) -> str:
    """Read a file from the sandbox filesystem.

    Args:
        path: Absolute path inside the sandbox (e.g. /workspace/main.py).
    """
    try:
        result = await ctx.deps.sandbox.read_file(ctx.deps.session_id, path)
        return str(result.get("content", result))
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
        await ctx.deps.sandbox.write_file(ctx.deps.session_id, path, content_b64)
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
        result = await ctx.deps.sandbox.list_files(ctx.deps.session_id, path)
        entries = result.get("entries", []) if isinstance(result, dict) else result
        if not entries:
            return f"{path} is empty"
        lines = []
        for e in entries:
            if isinstance(e, dict):
                prefix = "d" if e.get("is_dir") else "f"
                name = e.get("name", "?")
                size = f" ({e['size']}b)" if e.get("size") is not None else ""
            else:
                prefix = "f"
                name = str(e)
                size = ""
            lines.append(f"  [{prefix}] {name}{size}")
        return f"Contents of {path}:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listing {path}: {e}"
