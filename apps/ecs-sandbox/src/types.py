"""Domain types — single source of truth for session and event shapes.

These dataclasses define the canonical shapes returned by queries and services.
They also serve as the contract for the REST API and WebSocket protocol.
"""

from dataclasses import dataclass, field
from enum import Enum

# -- Enums -----------------------------------------------------------------


class SessionStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    DESTROYED = "destroyed"


class EventStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class EventKind(str, Enum):
    EXEC_SUBMIT = "exec_submit"
    GIT_CLONE = "git_clone"
    GIT_COMMIT = "git_commit"


# -- Sessions --------------------------------------------------------------


@dataclass
class Session:
    id: str
    status: SessionStatus
    container_id: str | None = None
    container_ip: str | None = None
    created_at: int = 0
    last_active_at: int = 0
    expires_at: int | None = None
    workspace_path: str | None = None
    metadata: dict = field(default_factory=dict)


# -- Events ----------------------------------------------------------------


@dataclass
class ExecPayload:
    cmd: str
    cwd: str = "/workspace"
    timeout_seconds: int = 300
    env: dict[str, str] | None = None


@dataclass
class ExecResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 1
    duration_ms: int = 0


@dataclass
class Event:
    session_id: str
    seq: int
    kind: EventKind
    status: EventStatus = EventStatus.PENDING
    payload: dict = field(default_factory=dict)
    result: dict | None = None
    submitted_at: int = 0
    completed_at: int | None = None


# -- WebSocket protocol ----------------------------------------------------


@dataclass
class WsOutput:
    """Server → client: command output."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 1
    duration_ms: int = 0
    cwd: str = "/workspace"

    def to_msg(self) -> dict:
        return {
            "type": "output",
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "cwd": self.cwd,
        }


@dataclass
class WsError:
    """Server → client: error message."""

    message: str

    def to_msg(self) -> dict:
        return {"type": "error", "message": self.message}


@dataclass
class WsHistory:
    """Server → client: replayed event history."""

    events: list[dict]

    def to_msg(self) -> dict:
        return {"type": "history", "events": self.events}


@dataclass
class WsSessionCreated:
    """Server → client: session created confirmation."""

    id: str

    def to_msg(self) -> dict:
        return {"type": "session_created", "id": self.id}
