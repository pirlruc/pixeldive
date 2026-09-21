"""JSON API routes for the pixeldive capture demo."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pixeldive_sdk import sample_session_payload

from demo.clients import DemoClients
from demo.download import continue_download, open_download
from demo.ui import PAGE
from demo.upload_body import write_upload

SdkFactory = Callable[[], Awaitable[DemoClients]]


def register_demo_routes(app: FastAPI, sdk: SdkFactory) -> None:
    """Attach HTML and JSON routes that proxy through the SDK."""

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        """Serve the capture console."""
        return PAGE

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        """Proxy liveness and readiness from the session service."""
        remote = await sdk()
        return {"health": await remote.health(), "ready": await remote.ready()}

    @app.post("/api/sessions")
    async def create_session() -> dict[str, Any]:
        """Create a session with the sample Android payload."""
        remote = await sdk()
        return await remote.create_session(sample_session_payload())

    @app.get("/api/sessions")
    async def list_sessions() -> dict[str, Any]:
        """List sessions from the session service."""
        remote = await sdk()
        return await remote.list_sessions()

    @app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: uuid.UUID) -> dict[str, str]:
        """Delete a session through the SDK."""
        remote = await sdk()
        await remote.delete_session(str(session_id))
        return {"deleted": str(session_id)}

    @app.get("/api/sessions/{session_id}/images")
    async def list_images(session_id: uuid.UUID) -> dict[str, Any]:
        """List images for one session."""
        remote = await sdk()
        return await remote.list_images(str(session_id))

    @app.post("/api/sessions/{session_id}/images")
    async def upload_image(session_id: uuid.UUID, file: UploadFile = File(...)) -> dict[str, Any]:
        """Upload a browser-selected or camera-captured image through the SDK."""
        remote = await sdk()
        path = await write_upload(file)
        try:
            return await remote.upload_image_from_path(
                str(session_id),
                str(path),
                filename=file.filename or "frame.png",
                content_type=file.content_type or "image/png",
            )
        finally:
            path.unlink(missing_ok=True)

    @app.get("/api/sessions/{session_id}/images/{image_id}/download")
    async def download_image(session_id: uuid.UUID, image_id: uuid.UUID) -> StreamingResponse:
        """Proxy a binary download through the SDK."""
        remote = await sdk()
        first, stream = await open_download(remote, str(session_id), str(image_id))
        return StreamingResponse(
            continue_download(first, stream),
            media_type="application/octet-stream",
        )
