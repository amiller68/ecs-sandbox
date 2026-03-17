"""Dev CLI — interactive agent REPL for testing the ecs-sandbox."""

from __future__ import annotations

import asyncio
import os
import uuid

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from dev_cli.agent.deps import AgentDeps
from dev_cli.agent.spec import build_agent
from ecs_sandbox import SandboxClient, CreateSessionRequest

console = Console()


async def run_repl(
    sandbox_url: str,
    sandbox_secret: str,
    anthropic_api_key: str,
    model: str,
    session_id: str | None,
) -> None:
    os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

    agent = build_agent(model=model)
    sid = session_id or str(uuid.uuid4())

    async with SandboxClient(sandbox_url, sandbox_secret) as sandbox:
        # Create a sandbox session
        console.print(f"[dim]Creating sandbox session {sid}...[/dim]")
        try:
            session = await sandbox.create_session(CreateSessionRequest(id=sid))
            console.print(
                Panel(
                    f"Session: {session.id}\nStatus: {session.status}",
                    title="Sandbox Ready",
                    border_style="green",
                )
            )
        except Exception as e:
            console.print(f"[red]Failed to create session: {e}[/red]")
            return

        deps = AgentDeps(sandbox=sandbox, session_id=sid)

        # Conversation history for multi-turn (memory only)
        message_history: list = []

        console.print(
            "[dim]Type your message, or 'quit' to exit. '/history' to view sandbox events.[/dim]\n"
        )

        while True:
            try:
                user_input = console.input("[bold cyan]you>[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input == "/history":
                try:
                    events = await sandbox.get_history(sid)
                    for ev in events:
                        cmd = ev.payload.get("cmd", ev.kind)
                        status_color = "green" if ev.status == "done" else "yellow"
                        console.print(
                            f"  [{status_color}][{ev.seq}][/{status_color}] {ev.status}: {cmd}"
                        )
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                continue
            if user_input == "/session":
                console.print(f"Session ID: {sid}")
                console.print(f"Sandbox URL: {sandbox_url}")
                continue

            try:
                result = await agent.run(
                    user_input,
                    deps=deps,
                    message_history=message_history,
                )

                # Accumulate message history for multi-turn
                message_history = result.all_messages()

                console.print()
                console.print(Markdown(result.data))
                console.print()

            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted.[/dim]")
            except Exception as e:
                console.print(f"\n[red]Agent error: {e}[/red]\n")

        # Cleanup
        console.print(f"\n[dim]Destroying session {sid}...[/dim]")
        try:
            await sandbox.destroy_session(sid)
            console.print("[green]Session destroyed.[/green]")
        except Exception as e:
            console.print(f"[yellow]Cleanup warning: {e}[/yellow]")


@click.command()
@click.option(
    "--sandbox-url",
    envvar="SANDBOX_URL",
    default="http://localhost:8000",
    help="ecs-sandbox API base URL.",
)
@click.option(
    "--sandbox-secret",
    envvar="SANDBOX_SECRET",
    required=True,
    help="ecs-sandbox API secret.",
)
@click.option(
    "--anthropic-api-key",
    envvar="ANTHROPIC_API_KEY",
    required=True,
    help="Anthropic API key for the agent.",
)
@click.option(
    "--model",
    envvar="AGENT_MODEL",
    default="claude-sonnet-4-5",
    help="Model to use for the agent.",
)
@click.option(
    "--session-id",
    envvar="SANDBOX_SESSION_ID",
    default=None,
    help="Reuse an existing sandbox session ID.",
)
def cli(
    sandbox_url: str,
    sandbox_secret: str,
    anthropic_api_key: str,
    model: str,
    session_id: str | None,
) -> None:
    """Interactive agent REPL for testing the ecs-sandbox."""
    console.print(
        Panel(
            "[bold]ecs-sandbox dev-cli[/bold]\n" "Interactive agent with sandbox tools",
            border_style="blue",
        )
    )
    asyncio.run(
        run_repl(sandbox_url, sandbox_secret, anthropic_api_key, model, session_id)
    )


if __name__ == "__main__":
    cli()
