"""Agent dependencies — memory-only, no persistence."""

from __future__ import annotations

from dataclasses import dataclass, field

from ecs_sandbox import SandboxClient


@dataclass
class AgentDeps:
    """Injected into every tool via RunContext."""

    sandbox: SandboxClient
    session_id: str
    messages: list[dict] = field(default_factory=list)
