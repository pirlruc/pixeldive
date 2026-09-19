"""Typed attributes shared by SessionService mixins."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import Principal
from app.config import Settings
from app.metrics import Metrics
from app.models import Session
from app.storage import StorageBackend


class SessionHost:
    """Attribute surface implemented by SessionService."""

    _factory: async_sessionmaker[AsyncSession]
    _storage: StorageBackend
    _settings: Settings
    _metrics: Metrics
    _write_sema: asyncio.Semaphore

    async def _require_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        principal: Principal | None = None,
        *,
        with_images: bool = False,
    ) -> Session:
        """Fetch a session inside an open unit of work (SessionService)."""
        raise NotImplementedError  # pragma: no cover
