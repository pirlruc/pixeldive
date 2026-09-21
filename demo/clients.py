"""REST + optional gRPC clients for the capture demo."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from pixeldive_sdk import GrpcClient, RestClient

from demo.image_json import session_image_json


class DemoClients:
    """Session CRUD over REST; image bytes over gRPC when a stub is bound."""

    def __init__(self, rest: RestClient, grpc: GrpcClient | None = None) -> None:
        """Bind clients. ``grpc`` is optional so tests can stay REST-only."""
        self.rest = rest
        self.grpc = grpc

    async def aclose(self) -> None:
        """Close both transports."""
        await self.rest.aclose()
        if self.grpc is not None:
            await self.grpc.aclose()

    async def health(self) -> dict[str, Any]:
        """Proxy liveness."""
        return await self.rest.health()

    async def ready(self) -> dict[str, Any]:
        """Proxy readiness."""
        return await self.rest.ready()

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a session over REST."""
        return await self.rest.create_session(payload)

    async def list_sessions(self) -> dict[str, Any]:
        """List sessions over REST."""
        return await self.rest.list_sessions()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session over REST."""
        await self.rest.delete_session(session_id)

    async def list_images(self, session_id: str) -> dict[str, Any]:
        """List image metadata over REST."""
        return await self.rest.list_images(session_id)

    async def upload_image(
        self,
        session_id: str,
        filename: str,
        payload: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload one image, preferring gRPC client-streaming."""
        if self.grpc is None:
            return await self.rest.upload_image(session_id, filename, payload, content_type)
        image = await self.grpc.upload_image(session_id, filename, payload, content_type)
        return session_image_json(image)

    async def upload_image_from_path(
        self,
        session_id: str,
        path: str,
        *,
        filename: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload one file from disk, preferring gRPC client-streaming."""
        if self.grpc is None:
            return await self.rest.upload_image_from_path(
                session_id,
                path,
                filename=filename,
                content_type=content_type,
            )
        image = await self.grpc.upload_image_from_path(
            session_id,
            path,
            filename=filename,
            content_type=content_type,
        )
        return session_image_json(image)

    async def upload_image_from_iter(
        self,
        session_id: str,
        pieces: AsyncIterator[bytes] | Iterator[bytes],
        *,
        filename: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Stream chunks over gRPC. REST still needs a file for multipart."""
        if self.grpc is None:
            raise RuntimeError("chunked upload requires a gRPC client")
        image = await self.grpc.upload_image_from_iter(
            session_id,
            pieces,
            filename=filename,
            content_type=content_type,
        )
        return session_image_json(image)

    def download_image(self, session_id: str, image_id: str) -> AsyncIterator[bytes]:
        """Download image bytes, preferring gRPC server-streaming."""
        if self.grpc is None:
            return self.rest.download_image(session_id, image_id)
        return self.grpc.download_image(session_id, image_id)
