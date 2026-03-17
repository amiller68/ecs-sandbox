"""FastAPI application factory."""

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from src.config import Config
from src.db.connection import get_engine, get_session_factory, apply_migrations
from src.middleware.auth import AuthMiddleware
from src.services.cleanup import get_active_sessions, mark_destroyed
from src.services.docker_manager import DockerManager
from src.services.worker import SessionWorker


async def _cleanup_stale_sessions(session_factory, docker: DockerManager) -> int:
    """Mark any active sessions as destroyed and remove their containers.

    After a server restart, old container IPs are stale and sessions are
    unreachable. This cleans them up automatically on startup.
    """
    async with session_factory() as db:
        sessions = await get_active_sessions(db)
        for row in sessions:
            if row["container_id"]:
                await docker.remove_container(row["container_id"])
            await mark_destroyed(db, row["id"])
        return len(sessions)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    config: Config = app.state.config

    # Database
    engine = get_engine(config.db_path)
    app.state.engine = engine
    app.state.session_factory = get_session_factory(engine)
    await apply_migrations(config.db_path)
    print("Database ready")

    # Redis (for background job dependencies)
    redis = Redis.from_url(config.redis_url)
    app.state.redis = redis
    print("Redis connected")

    # Docker manager
    docker = DockerManager(config)
    await docker.connect()
    app.state.docker = docker
    print("Docker connected")

    # Clean up stale sessions from previous run
    cleaned = await _cleanup_stale_sessions(app.state.session_factory, docker)
    print(f"Cleaned up {cleaned} stale session(s)")

    # Session worker
    worker = SessionWorker(app.state.session_factory)
    app.state.worker = worker
    print("Worker ready")

    yield

    # Shutdown
    await worker.stop_all()
    await docker.close()
    await redis.close()
    await engine.dispose()


def create_app(config: Config) -> FastAPI:
    app = FastAPI(
        title="ecs-sandbox",
        description="Remote sandbox execution environment for AI agents",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.config = config

    # Middleware
    app.add_middleware(AuthMiddleware, secret=config.sandbox_secret)  # type: ignore[arg-type]

    # Routers
    from src.routers import sandbox, fs, git, web

    app.include_router(sandbox.router)
    app.include_router(fs.router)
    app.include_router(git.router)
    app.include_router(web.router)

    # Static files for web terminal
    static_dir = pathlib.Path(__file__).parent / "static"
    app.mount("/web/static", StaticFiles(directory=static_dir), name="web-static")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
