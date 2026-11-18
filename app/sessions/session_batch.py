"""Image ingest mixed into SessionService (single frame and batch)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.blobs.uploads import discard_spool, new_image, persist_upload, upload_size, validate_upload
from app.exceptions import BatchLimitError
from app.models import ImageUpload, SessionImage
from app.sessions.auth import Principal
from app.sessions.session_host import SessionHost
from app.sessions.session_ops import apply_first_upload


class SessionBatchMixin(SessionHost):
    """Bounded fan-out ingest used by SessionService."""

    async def add_image(
        self,
        session_id: uuid.UUID,
        upload: ImageUpload,
        principal: Principal | None = None,
    ) -> SessionImage:
        """Validate, store, and attach a single image."""
        images = await self.add_images_batch(
            session_id,
            (upload,),
            principal,
            bounded=False,
        )
        return images[0]

    async def add_images_batch(
        self,
        session_id: uuid.UUID,
        uploads: Sequence[ImageUpload],
        principal: Principal | None = None,
        *,
        bounded: bool = True,
    ) -> list[SessionImage]:
        """Save payloads with bounded fan-out, then insert rows in one transaction."""
        if bounded:
            reject_bad_batch(uploads, self._settings.max_batch_images)
        try:
            for upload in uploads:
                await validate_upload(upload, self._settings)
            await self._quota.hit(principal)
            async with self._factory() as db:
                await self._require_session(db, session_id, principal)
            total = sum([await upload_size(item) for item in uploads])
            await self._quota.reserve_bytes(principal, session_id, total)
            try:
                return await self._commit_batch(session_id, uploads, principal)
            except Exception:
                await self._quota.release_bytes(principal, session_id, total)
                raise
        finally:
            for upload in uploads:
                await discard_spool(upload)

    async def _commit_batch(
        self,
        session_id: uuid.UUID,
        uploads: Sequence[ImageUpload],
        principal: Principal | None,
    ) -> list[SessionImage]:
        """Re-check the session, persist blobs, then insert image rows.

        Blobs written after the session disappears are deleted.
        """
        async with self._factory() as db:
            await self._require_session(db, session_id, principal)
        paths = await asyncio.gather(
            *[persist_upload(self._storage, item, self._write_sema) for item in uploads],
        )
        try:
            async with self._factory() as db:
                session = await self._require_session(db, session_id, principal)
                images = [
                    new_image(session, item, path)
                    for item, path in zip(uploads, paths, strict=True)
                ]
                db.add_all(images)
                if apply_first_upload(session):
                    db.add(session)
                await db.commit()
                for image in images:
                    await db.refresh(image)
        except Exception:
            await _delete_unreferenced(self, paths)
            raise
        self._metrics.observe_upload(sum([await upload_size(item) for item in uploads]))
        return images


async def _delete_unreferenced(host: SessionHost, paths: Sequence[str]) -> None:
    """Delete blobs this attempt wrote when no committed row still names them."""
    async with host._factory() as db:
        for path in paths:
            referenced = await db.scalar(
                select(func.count())
                .select_from(SessionImage)
                .where(SessionImage.storage_path == path),  # type: ignore[arg-type]
            )
            if not referenced:
                await host._storage.delete(path)


def reject_batch_count(count: int, max_images: int) -> None:
    """Reject a batch larger than ``max_images`` before any spool I/O."""
    if count > max_images:
        raise BatchLimitError(f"batch exceeds max_batch_images={max_images}")


def reject_bad_batch(uploads: Sequence[ImageUpload], max_images: int) -> None:
    """Reject empty or oversized batches before any I/O."""
    if not uploads:
        raise BatchLimitError("batch is empty")
    reject_batch_count(len(uploads), max_images)
