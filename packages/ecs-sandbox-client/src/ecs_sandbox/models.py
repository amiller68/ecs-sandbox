"""Pydantic response models for the ecs-sandbox API."""

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    id: str
    ttl_seconds: int = 1800
    image: str | None = None
    metadata: dict | None = None


class ExecRequest(BaseModel):
    cmd: str
    cwd: str = "/workspace"
    timeout_seconds: int = 300
    env: dict[str, str] | None = None
    sync: bool = False


class Session(BaseModel):
    id: str
    status: str
    container_id: str | None = None
    container_ip: str | None = None
    created_at: int
    last_active_at: int
    expires_at: int | None = None
    metadata: dict | None = None


class ExecResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class Event(BaseModel):
    id: int
    session_id: str
    seq: int
    kind: str
    status: str
    payload: dict | str
    result: dict | str | None = None
    submitted_at: int
    completed_at: int | None = None


class ExecSubmitResponse(BaseModel):
    seq: int
    status: str = "pending"
