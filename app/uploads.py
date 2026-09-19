"""Upload persistence helpers for SessionService."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.filenames import sanitize_filename
from app.models import ImageUpload, Session, SessionImage
from app.spool import Spool
from app.storage import StorageBackend
from app.upload_validate import upload_size, validate_upload

__all__ = [
    "discard_spool",
    "new_image",
    "persist_upload",
    "upload_from_spool",
    "upload_size",
    "validate_upload",
]


def upload_from_spool(
    filename: str,
    content_type: str,
    spool: Spool,
    extra: dict[str, Any] | None = None,
) -> ImageUpload:
    """Build an ImageUpload that points at a hashed spool file."""
    return ImageUpload(
        filename=sanitize_filename(filename),
        content_type=content_type,
        payload=b"",
        extra_metadata=extra or {},
        spool_path=str(spool.path),
        digest_hex=spool.digest_hex,
        size_bytes=spool.size_bytes,
    )


def new_image(session: Session, upload: ImageUpload, storage_path: str) -> SessionImage:
    """Build an unsaved SessionImage row."""
    return SessionImage(
        session_id=session.id,
        filename=sanitize_filename(upload.filename),
        content_type=upload.content_type,
        size_bytes=upload_size(upload),
        storage_path=storage_path,
        extra_metadata=upload.extra_metadata,
    )


async def persist_upload(
    storage: StorageBackend,
    upload: ImageUpload,
    semaphore: asyncio.Semaphore,
) -> str:
    """Save a spool or in-memory payload under the write semaphore."""
    async with semaphore:
        if upload.spool_path and upload.digest_hex:
            return await storage.save_file(
                Path(upload.spool_path),
                upload.digest_hex,
                upload.content_type,
            )
        return await storage.save(upload.payload, upload.content_type)


async def discard_spool(upload: ImageUpload) -> None:
    """Delete a spool file after it has been copied into storage."""
    if not upload.spool_path:
        return
    try:
        import aiofiles.os

        await aiofiles.os.remove(upload.spool_path)
    except FileNotFoundError:
        return
