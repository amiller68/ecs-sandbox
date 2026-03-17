"""Router dependency helpers — build Context from FastAPI request state."""

from starlette.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession

from src.services._context import Context


def context_from_request(conn: HTTPConnection, db: AsyncSession) -> Context:
    """Build a service Context from the current request/websocket's app state."""
    return Context(
        db=db,
        docker=conn.app.state.docker,
        config=conn.app.state.config,
        worker=conn.app.state.worker,
    )
