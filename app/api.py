"""FastAPI REST transport for SessionService (API-001)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, Depends, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.exceptions import ImageTooLargeError
from app.http_errors import register_error_handlers
from app.metadata import parse_metadata_json
from app.models import (
    ImageUpload,
    Session,
    SessionCreate,
    SessionImage,
    SessionImageRead,
    SessionRead,
    SessionUpdate,
)
from app.service import SessionService


async def current_service(request: Request) -> SessionService:
    """Resolve the process-wide SessionService from app state."""
    return cast(SessionService, request.app.state.service)


def create_app(service: SessionService) -> FastAPI:
    """Build a FastAPI app bound to a SessionService instance."""
    app = FastAPI(title="pixeldive session service", version="0.1.0")
    app.state.service = service
    app.include_router(_router)
    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe for Docker HEALTHCHECK and load balancers."""
        return {"status": "ok"}

    return app


_router = APIRouter(prefix="/api/v1")


@_router.post("/sessions", status_code=201, response_model=SessionRead)
async def create_session(
    payload: SessionCreate,
    service: SessionService = Depends(current_service),
) -> Session:
    """Create a session with Android device and camera JSON."""
    return await service.create_session(payload)


@_router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: uuid.UUID,
    service: SessionService = Depends(current_service),
) -> Session:
    """Return session metadata and device specifications."""
    return await service.get_session(session_id)


@_router.put("/sessions/{session_id}", response_model=SessionRead)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    service: SessionService = Depends(current_service),
) -> Session:
    """Update session status or associated metadata."""
    return await service.update_session(session_id, payload)


@_router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    service: SessionService = Depends(current_service),
) -> Response:
    """Delete a session, cascading image rows and unreferenced blobs."""
    await service.delete_session(session_id)
    return Response(status_code=204)


@_router.post("/sessions/{session_id}/images", status_code=201, response_model=SessionImageRead)
async def upload_image(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    service: SessionService = Depends(current_service),
) -> SessionImage:
    """Upload a single image via multipart/form-data."""
    upload = await _to_upload(file, metadata, service)
    return await service.add_image(session_id, upload)


@_router.post(
    "/sessions/{session_id}/images/batch",
    status_code=201,
    response_model=list[SessionImageRead],
)
async def upload_images_batch(
    session_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    metadata: str | None = Form(default=None),
    service: SessionService = Depends(current_service),
) -> list[SessionImage]:
    """Upload multiple files in one multipart request."""
    extra = parse_metadata_json(metadata)
    uploads = [await _to_upload(item, None, service, extra=extra) for item in files]
    return await service.add_images_batch(session_id, uploads)


@_router.get("/sessions/{session_id}/images", response_model=list[SessionImageRead])
async def list_images(
    session_id: uuid.UUID,
    service: SessionService = Depends(current_service),
) -> list[SessionImage]:
    """List image metadata for a session."""
    return await service.list_images(session_id)


@_router.get("/sessions/{session_id}/images/{image_id}")
async def download_image(
    session_id: uuid.UUID,
    image_id: uuid.UUID,
    service: SessionService = Depends(current_service),
) -> StreamingResponse:
    """Stream the raw image binary."""
    image = await service.get_image(session_id, image_id)

    async def chunks() -> AsyncIterator[bytes]:
        async for chunk in service.stream_image(session_id, image_id):
            yield chunk

    return StreamingResponse(
        chunks(),
        media_type=image.content_type,
        headers={"Content-Disposition": f'attachment; filename="{image.filename}"'},
    )


async def _to_upload(
    file: UploadFile,
    metadata: str | None,
    service: SessionService,
    extra: dict | None = None,
) -> ImageUpload:
    """Read an UploadFile into an ImageUpload with size enforcement."""
    payload = await _read_limited(file, service._settings.max_image_bytes)
    return ImageUpload(
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        payload=payload,
        extra_metadata=extra if extra is not None else parse_metadata_json(metadata),
    )


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload, aborting when it exceeds ``max_bytes``."""
    buffer = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise ImageTooLargeError(f"image exceeds max_image_bytes={max_bytes}")
    return bytes(buffer)
