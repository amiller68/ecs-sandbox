"""Service-layer context for dependency injection."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Config
from src.services.docker_manager import DockerManager
from src.services.worker import SessionWorker


@dataclass
class Context:
    db: AsyncSession
    docker: DockerManager
    config: Config
    worker: SessionWorker
