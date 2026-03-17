"""
Task dependency injection helpers using TaskiqDepends.

These dependencies are resolved by taskiq-fastapi when running in worker context,
providing access to database sessions and Redis via the FastAPI app state.

Usage in tasks:
    from src.tasks.deps import get_db_session, get_redis

    @broker.task
    async def my_task(
        db: AsyncSession = TaskiqDepends(get_db_session),
        redis: Redis = TaskiqDepends(get_redis),
    ) -> dict:
        ...
"""

from typing import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends


async def get_db_session(
    request: Request = TaskiqDepends(),
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session from FastAPI app state."""
    async with request.app.state.session_factory() as session:
        yield session


async def get_redis(request: Request = TaskiqDepends()) -> Redis:
    """Get Redis client from FastAPI app state."""
    return request.app.state.redis
