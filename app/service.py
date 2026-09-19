"""Unified session and image business logic (ARCH-001).

FastAPI and gRPC call these methods; they never touch SQL or disk themselves.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlmodel import col

from app.config import Settings
from app.content_types import ALLOWED_CONTENT_TYPES
from app.exceptions import (
    BatchLimitError,
    EmptyImageError,
    ImageNotFoundError,
    ImageTooLargeError,
    InvalidStatusError,
    SessionNotFoundError,
    UnsupportedContentTypeError,
)
from app.filenames import sanitize_filename
from app.models import (
    ImageUpload,
    Session,
    SessionCreate,
    SessionImage,
    SessionStatus,
    SessionUpdate,
    utcnow,
)
from app.storage import StorageBackend


class SessionService:
    """Sessions, image rows, and blob lifecycle."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        storage: StorageBackend,
        settings: Settings,
    ) -> None:
        """Bind the DB session factory, blob store, and size limits."""
        self._factory = factory
        self._storage = storage
        self._settings = settings

    async def create_session(self, payload: SessionCreate) -> Session:
        """Insert a CREATED session with Android device JSON."""
        record = Session(
            session_name=payload.session_name,
            status=SessionStatus.CREATED.value,
            phone_info=payload.phone_info,
            phone_capabilities=payload.phone_capabilities,
            camera_capabilities=payload.camera_capabilities,
            extra_metadata=payload.extra_metadata,
        )
        async with self._factory() as db:
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    async def get_session(self, session_id: uuid.UUID) -> Session:
        """Load a session or raise SessionNotFoundError."""
        async with self._factory() as db:
            return await self._require_session(db, session_id)

    async def update_session(self, session_id: uuid.UUID, patch: SessionUpdate) -> Session:
        """Apply optional name/status/metadata updates."""
        updates = patch.model_dump(exclude_none=True, by_alias=False)
        if "status" in updates:
            updates["status"] = _status_value(updates["status"])
        async with self._factory() as db:
            record = await self._require_session(db, session_id)
            for key, value in updates.items():
                setattr(record, key, value)
            record.updated_at = utcnow()
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    async def delete_session(self, session_id: uuid.UUID) -> None:
        """Delete the session row (cascade images) and GC unreferenced blobs."""
        async with self._factory() as db:
            record = await self._require_session(db, session_id, with_images=True)
            paths = [image.storage_path for image in record.images]
            await db.delete(record)
            await db.commit()
        await self._gc_paths(paths)

    async def add_image(self, session_id: uuid.UUID, upload: ImageUpload) -> SessionImage:
        """Validate, store, and attach a single image."""
        self.validate_upload(upload)
        storage_path = await self._storage.save(upload.payload, upload.content_type)
        async with self._factory() as db:
            session = await self._require_session(db, session_id)
            image = self._new_image(session, upload, storage_path)
            _touch_in_progress(session)
            db.add(image)
            db.add(session)
            await db.commit()
            await db.refresh(image)
            return image

    async def add_images_batch(
        self,
        session_id: uuid.UUID,
        uploads: Sequence[ImageUpload],
    ) -> list[SessionImage]:
        """Save payloads concurrently, then insert rows in one transaction."""
        if not uploads:
            raise BatchLimitError("batch is empty")
        if len(uploads) > self._settings.max_batch_images:
            raise BatchLimitError(
                f"batch exceeds max_batch_images={self._settings.max_batch_images}",
            )
        for upload in uploads:
            self.validate_upload(upload)
        async with self._factory() as db:
            session = await self._require_session(db, session_id)
        paths = await asyncio.gather(
            *[self._storage.save(item.payload, item.content_type) for item in uploads],
        )
        async with self._factory() as db:
            session = await self._require_session(db, session_id)
            images = [
                self._new_image(session, item, path)
                for item, path in zip(uploads, paths, strict=True)
            ]
            _touch_in_progress(session)
            db.add_all(images)
            db.add(session)
            await db.commit()
            for image in images:
                await db.refresh(image)
            return images

    async def list_images(self, session_id: uuid.UUID) -> list[SessionImage]:
        """Return image metadata for a session."""
        async with self._factory() as db:
            await self._require_session(db, session_id)
            statement = (
                select(SessionImage)
                .where(SessionImage.session_id == session_id)  # type: ignore[arg-type]
                .order_by(SessionImage.uploaded_at)  # type: ignore[arg-type]
            )
            result = await db.execute(statement)
            return list(result.scalars().all())

    async def get_image(self, session_id: uuid.UUID, image_id: uuid.UUID) -> SessionImage:
        """Load one image row scoped to a session."""
        async with self._factory() as db:
            await self._require_session(db, session_id)
            image = await db.get(SessionImage, image_id)
            if image is None or image.session_id != session_id:
                raise ImageNotFoundError(f"image {image_id} not found")
            return image

    async def stream_image(
        self,
        session_id: uuid.UUID,
        image_id: uuid.UUID,
    ) -> AsyncIterator[bytes]:
        """Yield stored bytes for download endpoints."""
        image = await self.get_image(session_id, image_id)
        try:
            async for chunk in self._storage.stream(
                image.storage_path,
                self._settings.download_chunk_bytes,
            ):
                yield chunk
        except FileNotFoundError as exc:
            raise ImageNotFoundError(f"image {image_id} blob is missing") from exc

    def validate_upload(self, upload: ImageUpload) -> None:
        """Reject empty, oversized, or non-image payloads."""
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedContentTypeError(f"unsupported content type: {upload.content_type}")
        if not upload.payload:
            raise EmptyImageError("image payload is empty")
        if len(upload.payload) > self._settings.max_image_bytes:
            raise ImageTooLargeError(
                f"image exceeds max_image_bytes={self._settings.max_image_bytes}",
            )
        upload.content_type = content_type

    def _new_image(self, session: Session, upload: ImageUpload, storage_path: str) -> SessionImage:
        """Build an unsaved SessionImage row."""
        return SessionImage(
            session_id=session.id,
            filename=sanitize_filename(upload.filename),
            content_type=upload.content_type,
            size_bytes=len(upload.payload),
            storage_path=storage_path,
            extra_metadata=upload.extra_metadata,
        )

    async def _require_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        *,
        with_images: bool = False,
    ) -> Session:
        """Fetch a session inside an open unit of work."""
        statement = select(Session).where(Session.id == session_id)  # type: ignore[arg-type]
        if with_images:
            statement = statement.options(selectinload(Session.images))  # type: ignore[arg-type]
        result = await db.execute(statement)
        record = result.scalar_one_or_none()
        if record is None:
            raise SessionNotFoundError(f"session {session_id} not found")
        return record

    async def _gc_paths(self, paths: Sequence[str]) -> None:
        """Delete blobs whose storage_path is no longer referenced."""
        unique_paths = list(dict.fromkeys(paths))
        if not unique_paths:
            return
        async with self._factory() as db:
            statement = (
                select(col(SessionImage.storage_path))
                .where(col(SessionImage.storage_path).in_(unique_paths))
                .distinct()
            )
            still_used = set((await db.execute(statement)).scalars().all())
        for path in unique_paths:
            if path not in still_used:
                await self._storage.delete(path)


def _status_value(status: SessionStatus | str) -> str:
    """Normalize and validate a status string."""
    value = status.value if isinstance(status, SessionStatus) else str(status)
    allowed = {item.value for item in SessionStatus}
    if value not in allowed:
        raise InvalidStatusError(f"invalid status: {value}")
    return value


def _touch_in_progress(session: Session) -> None:
    """Move CREATED sessions to IN_PROGRESS on first successful upload."""
    if session.status == SessionStatus.CREATED.value:
        session.status = SessionStatus.IN_PROGRESS.value
    session.updated_at = utcnow()
