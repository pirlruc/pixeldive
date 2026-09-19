"""REST image upload, list, and download routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api_deps import PrincipalDep, ServiceDep
from app.disposition import attachment_disposition
from app.filenames import sanitize_filename
from app.metadata import parse_metadata_json
from app.models import ImagePage, ImageUpload, SessionImage, SessionImageRead
from app.service import SessionService
from app.spool import spool_chunks
from app.uploads import upload_from_spool

image_router = APIRouter(prefix="/api/v1")


@image_router.post(
    "/sessions/{session_id}/images",
    status_code=201,
    response_model=SessionImageRead,
)
async def upload_image(
    session_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
) -> SessionImage:
    """Upload a single image via multipart/form-data."""
    upload = await to_upload(file, metadata, service)
    return await service.add_image(session_id, upload, principal)


@image_router.post(
    "/sessions/{session_id}/images/batch",
    status_code=201,
    response_model=list[SessionImageRead],
)
async def upload_images_batch(
    session_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
    files: list[UploadFile] = File(...),
    metadata: str | None = Form(default=None),
) -> list[SessionImage]:
    """Upload multiple files in one multipart request."""
    extra = parse_metadata_json(metadata)
    uploads = [await to_upload(item, None, service, extra=extra) for item in files]
    return await service.add_images_batch(session_id, uploads, principal)


@image_router.get("/sessions/{session_id}/images", response_model=ImagePage)
async def list_images(
    session_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
    limit: int = Query(default=50, ge=1),
    cursor: str | None = None,
) -> ImagePage:
    """List image metadata for a session."""
    page = await service.list_images(
        session_id,
        limit=limit,
        cursor=cursor,
        principal=principal,
    )
    return ImagePage(
        items=[SessionImageRead.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
    )


@image_router.get("/sessions/{session_id}/images/{image_id}")
async def download_image(
    session_id: uuid.UUID,
    image_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
) -> StreamingResponse:
    """Stream the raw image binary."""
    image = await service.get_image(session_id, image_id, principal)

    async def chunks() -> AsyncIterator[bytes]:
        async for chunk in service.stream_image(session_id, image_id, principal):
            yield chunk

    return StreamingResponse(
        chunks(),
        media_type=image.content_type,
        headers={"Content-Disposition": attachment_disposition(image.filename)},
    )


async def file_chunks(file: UploadFile) -> AsyncIterator[bytes]:
    """Yield multipart chunks from an UploadFile."""
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        yield chunk


async def to_upload(
    file: UploadFile,
    metadata: str | None,
    service: SessionService,
    extra: dict[str, Any] | None = None,
) -> ImageUpload:
    """Spool an UploadFile to disk while hashing incrementally."""
    spool = await spool_chunks(
        file_chunks(file),
        service._settings.spool_dir(),
        service._settings.max_image_bytes,
    )
    return upload_from_spool(
        sanitize_filename(file.filename),
        file.content_type or "application/octet-stream",
        spool,
        extra if extra is not None else parse_metadata_json(metadata),
    )
