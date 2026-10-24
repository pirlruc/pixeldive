"""PostgreSQL-backed quota counters shared by app replicas (SEC-004)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.sessions.quota_limits import QuotaLimits
from app.sessions.quota_sql_ops import record_hit, release_both, reserve_both
from app.sessions.quota_sql_rows import tenant_scope


def open_engine(database_url: str) -> AsyncEngine:
    """Open a short-lived engine. SQLite uses a null pool so tests can share a file."""
    if database_url.startswith("sqlite"):
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            connect_args={"timeout": 30},
        )
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 5},
    )


class SqlQuotaStore:
    """SQL quota rows. PostgreSQL locks the row; other dialects share sequentially."""

    def __init__(self, database_url: str) -> None:
        """Remember the URL and connect on the first enforced operation."""
        self._url = database_url
        self._held: AsyncEngine | None = None

    async def aclose(self) -> None:
        """Dispose the engine if one was opened."""
        if self._held is not None:
            await self._held.dispose()
            self._held = None

    async def hit(self, owner_id: str, limits: QuotaLimits) -> None:
        """Count one wall-clock hit under a row lock."""
        async with self._engine().begin() as conn:
            await record_hit(conn, tenant_scope(owner_id), limits, self._url)

    async def reserve(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Reserve bytes. A failed check rolls the transaction back."""
        async with self._engine().begin() as conn:
            await reserve_both(conn, owner_id, session_id, nbytes, limits, self._url)

    async def release(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Return reserved bytes for the caps that are enabled."""
        async with self._engine().begin() as conn:
            await release_both(conn, owner_id, session_id, nbytes, limits, self._url)

    def _engine(self) -> AsyncEngine:
        """Create the engine on first use so a down database fails the request."""
        if self._held is not None:
            return self._held
        if not self._url.strip():
            msg = "quota database url is empty"
            raise RuntimeError(msg)
        self._held = open_engine(self._url)
        return self._held
