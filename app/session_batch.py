"""Image ingest mixed into SessionService (single frame and batch)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence

from app.auth import Principal
from app.exceptions import BatchLimitError
from app.models import ImageUpload, SessionImage
from app.session_host import SessionHost
from app.session_ops import apply_first_upload
from app.uploads import discard_spool, new_image, persist_upload, upload_size, validate_upload


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
                validate_upload(upload, self._settings)
            self._quota.hit(principal)
            async with self._factory() as db:
                await self._require_session(db, session_id, principal)
            total = sum(upload_size(item) for item in uploads)
            self._quota.reserve_bytes(principal, session_id, total)
            try:
                return await self._commit_batch(session_id, uploads, principal)
            except Exception:
                self._quota.release_bytes(principal, session_id, total)
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
        """Persist blobs then insert image rows."""
        paths = await asyncio.gather(
            *[persist_upload(self._storage, item, self._write_sema) for item in uploads],
        )
        async with self._factory() as db:
            session = await self._require_session(db, session_id, principal)
            images = [
                new_image(session, item, path) for item, path in zip(uploads, paths, strict=True)
            ]
            db.add_all(images)
            if apply_first_upload(session):
                db.add(session)
            await db.commit()
            for image in images:
                await db.refresh(image)
        self._metrics.observe_upload(sum(upload_size(item) for item in uploads))
        return images


def reject_bad_batch(uploads: Sequence[ImageUpload], max_images: int) -> None:
    """Reject empty or oversized batches before any I/O."""
    if not uploads:
        raise BatchLimitError("batch is empty")
    if len(uploads) > max_images:
        raise BatchLimitError(f"batch exceeds max_batch_images={max_images}")
