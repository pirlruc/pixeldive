"""JSON API routes for the pixeldive capture demo."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pixeldive_sdk import RestClient, sample_session_payload

from demo.ui import PAGE

SdkFactory = Callable[[], Awaitable[RestClient]]


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
    async def delete_session(session_id: str) -> dict[str, str]:
        """Delete a session through the SDK."""
        remote = await sdk()
        await remote.delete_session(session_id)
        return {"deleted": session_id}

    @app.get("/api/sessions/{session_id}/images")
    async def list_images(session_id: str) -> dict[str, Any]:
        """List images for one session."""
        remote = await sdk()
        return await remote.list_images(session_id)

    @app.post("/api/sessions/{session_id}/images")
    async def upload_image(session_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
        """Upload a browser-selected image through the SDK."""
        remote = await sdk()
        payload = await file.read()
        return await remote.upload_image(
            session_id,
            file.filename or "frame.png",
            payload,
            file.content_type or "image/png",
        )

    @app.get("/api/sessions/{session_id}/images/{image_id}/download")
    async def download_image(session_id: str, image_id: str) -> StreamingResponse:
        """Proxy a binary download through the SDK."""
        remote = await sdk()

        async def chunks() -> AsyncIterator[bytes]:
            async for chunk in remote.download_image(session_id, image_id):
                yield chunk

        return StreamingResponse(chunks(), media_type="application/octet-stream")
