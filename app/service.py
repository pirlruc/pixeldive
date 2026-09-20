"""Unified session and image business logic (ARCH-001).

FastAPI and gRPC call these methods; they never touch SQL or disk themselves.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.auth import Principal
from app.blob_gc import gc_unreferenced, sweep_orphans
from app.config import Settings
from app.exceptions import SessionNotFoundError
from app.metrics import Metrics
from app.models import Session, SessionCreate, SessionStatus, SessionUpdate, utcnow
from app.quotas import quota_from_settings
from app.session_batch import SessionBatchMixin
from app.session_list import SessionListMixin
from app.session_ops import SessionOpsMixin
from app.session_patch import apply_metadata, status_value
from app.storage import StorageBackend


class SessionService(SessionListMixin, SessionOpsMixin, SessionBatchMixin):
    """Sessions, image rows, and blob lifecycle."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        storage: StorageBackend,
        settings: Settings,
        metrics: Metrics | None = None,
    ) -> None:
        """Bind the DB session factory, blob store, and size limits."""
        self._factory = factory
        self._storage = storage
        self._settings = settings
        self._metrics = metrics or Metrics()
        self._write_sema = asyncio.Semaphore(settings.max_concurrent_saves)
        self._quota = quota_from_settings(
            settings.rate_limit_per_minute,
            settings.rate_limit_window_seconds,
            settings.tenant_max_upload_bytes,
            settings.session_max_upload_bytes,
        )

    async def ping_db(self) -> None:
        """Raise if the database cannot be reached (readiness)."""
        async with self._factory() as db:
            await db.execute(text("SELECT 1"))

    async def create_session(
        self,
        payload: SessionCreate,
        principal: Principal | None = None,
    ) -> Session:
        """Insert a CREATED session with Android device JSON."""
        self._quota.hit(principal)
        record = Session(
            session_name=payload.session_name,
            status=SessionStatus.CREATED.value,
            phone_info=payload.phone_info,
            phone_capabilities=payload.phone_capabilities,
            camera_capabilities=payload.camera_capabilities,
            extra_metadata=payload.extra_metadata,
            owner_id=principal.owner_id if principal else None,
        )
        async with self._factory() as db:
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    async def get_session(
        self,
        session_id: uuid.UUID,
        principal: Principal | None = None,
    ) -> Session:
        """Load a session or raise SessionNotFoundError."""
        self._quota.hit(principal)
        async with self._factory() as db:
            return await self._require_session(db, session_id, principal)

    async def update_session(
        self,
        session_id: uuid.UUID,
        patch: SessionUpdate,
        principal: Principal | None = None,
    ) -> Session:
        """Apply optional name/status/metadata updates (replace or merge)."""
        self._quota.hit(principal)
        updates = patch.model_dump(exclude_none=True, by_alias=False)
        merge = bool(updates.pop("merge_metadata", False))
        if "status" in updates:
            updates["status"] = status_value(updates["status"])
        incoming_meta = updates.pop("extra_metadata", None)
        async with self._factory() as db:
            record = await self._require_session(db, session_id, principal)
            for key, value in updates.items():
                setattr(record, key, value)
            if incoming_meta is not None:
                record.extra_metadata = apply_metadata(record.extra_metadata, incoming_meta, merge)
            record.updated_at = utcnow()
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    async def delete_session(
        self,
        session_id: uuid.UUID,
        principal: Principal | None = None,
    ) -> None:
        """Delete the session row (cascade images) and GC unreferenced blobs."""
        self._quota.hit(principal)
        async with self._factory() as db:
            record = await self._require_session(db, session_id, principal, with_images=True)
            paths = [image.storage_path for image in record.images]
            await db.delete(record)
            await db.commit()
        await gc_unreferenced(
            self._factory,
            self._storage,
            paths,
            min_age_seconds=self._settings.gc_min_age_seconds,
        )

    async def sweep_orphans(self, min_age_seconds: float | None = None) -> int:
        """Reclaim unreferenced blobs older than the configured grace period."""
        age = self._settings.orphan_min_age_seconds if min_age_seconds is None else min_age_seconds
        return await sweep_orphans(self._factory, self._storage, min_age_seconds=age)

    async def _require_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        principal: Principal | None = None,
        *,
        with_images: bool = False,
    ) -> Session:
        """Fetch a session inside an open unit of work and enforce ownership."""
        statement = select(Session).where(Session.id == session_id)  # type: ignore[arg-type]
        if with_images:
            statement = statement.options(selectinload(Session.images))  # type: ignore[arg-type]
        result = await db.execute(statement)
        record = result.scalar_one_or_none()
        if record is None or _wrong_owner(record, principal):
            raise SessionNotFoundError(f"session {session_id} not found")
        return record


def _wrong_owner(record: Session, principal: Principal | None) -> bool:
    """True when an authenticated caller does not own ``record`` (SEC-003)."""
    return principal is not None and record.owner_id != principal.owner_id
