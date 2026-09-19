"""Async SQLAlchemy/SQLModel engine and session factory."""

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an AsyncEngine for PostgreSQL (asyncpg) or SQLite (aiosqlite)."""
    url = settings.database_url
    kwargs: dict[str, object] = {"echo": False, "future": True, "connect_args": {}}
    if not url.startswith("sqlite"):
        kwargs["pool_pre_ping"] = settings.db_pool_pre_ping
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    engine = create_async_engine(url, **kwargs)  # type: ignore[arg-type]
    if url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """SQLite foreign keys are off until PRAGMA foreign_keys=ON (DATA-001)."""

    def _on_connect(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(engine.sync_engine, "connect", _on_connect)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to ``engine``."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create tables if they do not already exist (test/dev)."""
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a short-lived AsyncSession (used by tests and optional deps)."""
    async with factory() as session:
        yield session
