"""Image lookup and download operations mixed into SessionService."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.auth import Principal
from app.exceptions import ImageNotFoundError
from app.models import ImageUpload, Session, SessionImage, SessionStatus, utcnow
from app.session_host import SessionHost
from app.uploads import validate_upload


class SessionOpsMixin(SessionHost):
    """Single-image lookup helpers used by SessionService."""

    async def get_image(
        self,
        session_id: uuid.UUID,
        image_id: uuid.UUID,
        principal: Principal | None = None,
    ) -> SessionImage:
        """Load one image row scoped to a session."""
        self._quota.hit(principal)
        async with self._factory() as db:
            await self._require_session(db, session_id, principal)
            image = await db.get(SessionImage, image_id)
            if image is None or image.session_id != session_id:
                raise ImageNotFoundError(f"image {image_id} not found")
            return image

    async def stream_image(
        self,
        session_id: uuid.UUID,
        image_id: uuid.UUID,
        principal: Principal | None = None,
        *,
        image: SessionImage | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield stored bytes for download endpoints.

        Pass ``image`` when the caller already loaded the row so download does
        not consume a second quota hit or extra DB round-trip.
        """
        row = image or await self.get_image(session_id, image_id, principal)
        if row.session_id != session_id or row.id != image_id:
            raise ImageNotFoundError(f"image {image_id} not found")
        try:
            async for chunk in self._storage.stream(
                row.storage_path,
                self._settings.download_chunk_bytes,
            ):
                yield chunk
        except FileNotFoundError as exc:
            raise ImageNotFoundError(f"image {image_id} blob is missing") from exc

    def validate_upload(self, upload: ImageUpload) -> None:
        """Reject empty, oversized, or non-image payloads."""
        validate_upload(upload, self._settings)


def apply_first_upload(session: Session) -> bool:
    """Move CREATED sessions to IN_PROGRESS. Skip later per-frame session writes."""
    if session.status != SessionStatus.CREATED.value:
        return False
    session.status = SessionStatus.IN_PROGRESS.value
    session.updated_at = utcnow()
    return True
