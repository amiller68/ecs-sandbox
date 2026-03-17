"""Builds the pydantic-ai Agent for sandbox interaction."""

from __future__ import annotations

from pydantic_ai import Agent

from dev_cli.agent.deps import AgentDeps
from dev_cli.tools.sandbox_exec import sandbox_exec
from dev_cli.tools.sandbox_exec_sync import sandbox_exec_sync
from dev_cli.tools.sandbox_fs import (
    sandbox_read_file,
    sandbox_write_file,
    sandbox_list_files,
)
from dev_cli.tools.sandbox_session import sandbox_session_info

SYSTEM_PROMPT = """\
You are a development assistant with access to a remote sandbox environment.
The sandbox is an isolated Linux container where you can execute shell commands,
read and write files, and explore the filesystem.

Use the sandbox tools to help the user accomplish tasks. When asked to run code,
write scripts, or explore a system, use the sandbox execution tools.

Guidelines:
- Use sandbox_exec_sync for quick commands (< 30s): ls, cat, echo, pip install, etc.
- Use sandbox_exec for long-running commands, then check results via session history.
- Use the filesystem tools for reading/writing files directly.
- Always check command output for errors and report them clearly.
- The sandbox workspace is at /workspace by default.
"""


def build_agent(model: str = "claude-sonnet-4-5") -> Agent[AgentDeps, str]:
    agent = Agent(
        model,
        system_prompt=SYSTEM_PROMPT,
        deps_type=AgentDeps,
    )

    # Register all tools (agent.tool() returns a decorator)
    agent.tool()(sandbox_exec)
    agent.tool()(sandbox_exec_sync)
    agent.tool()(sandbox_read_file)
    agent.tool()(sandbox_write_file)
    agent.tool()(sandbox_list_files)
    agent.tool()(sandbox_session_info)

    return agent
