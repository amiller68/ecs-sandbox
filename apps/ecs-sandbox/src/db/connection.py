"""SQLite database connection and migration management."""

import os

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def get_engine(db_path: str | None = None):
    path = db_path or os.getenv("DB_PATH", "/data/ecs-sandbox.db")
    url = f"sqlite+aiosqlite:///{path}"
    return create_async_engine(url, echo=False)


def get_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def apply_migrations(db_path: str | None = None):
    """Apply SQLite schema migrations (plain SQL files in migrations/)."""
    path = db_path or os.getenv("DB_PATH", "/data/ecs-sandbox.db")
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        # Apply pragmas
        await conn.execute(sqlalchemy.text("PRAGMA journal_mode = WAL"))
        await conn.execute(sqlalchemy.text("PRAGMA synchronous = NORMAL"))
        await conn.execute(sqlalchemy.text("PRAGMA foreign_keys = ON"))
        await conn.execute(sqlalchemy.text("PRAGMA busy_timeout = 5000"))

        # Apply migration files in order
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if os.path.exists(migrations_dir):
            sql_files = sorted(
                f for f in os.listdir(migrations_dir) if f.endswith(".sql")
            )
            for sql_file in sql_files:
                with open(os.path.join(migrations_dir, sql_file)) as f:
                    sql_content = f.read()
                for statement in sql_content.split(";"):
                    statement = statement.strip()
                    if statement:
                        await conn.execute(sqlalchemy.text(statement))

    await engine.dispose()
