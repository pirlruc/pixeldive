"""Session and image RPCs for ``GrpcClient``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_mapping import create_session_request
from pixeldive_sdk.samples import sample_session_payload


class GrpcCallsMixin:
    """RPCs that require an open stub."""

    async def connect(self) -> None:
        """Open the channel; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _metadata(self) -> list[tuple[str, str]]:
        """Invocation metadata; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _require_stub(self) -> pb_grpc.SessionServiceStub:
        """Return the stub; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    async def create_session(self, payload: dict[str, Any] | None = None) -> pb.Session:
        """Create a session from a REST-shaped dict (defaults to the demo payload)."""
        await self.connect()
        body = payload or sample_session_payload()
        response = await self._require_stub().CreateSession(
            create_session_request(body),
            metadata=self._metadata(),
        )
        return cast(pb.Session, response.session)

    async def list_sessions(self, *, limit: int = 50, cursor: str = "") -> pb.SessionListResponse:
        """List sessions with a cursor."""
        await self.connect()
        response = await self._require_stub().ListSessions(
            pb.ListSessionsRequest(limit=limit, cursor=cursor),
            metadata=self._metadata(),
        )
        return cast(pb.SessionListResponse, response)

    async def upload_image(
        self,
        session_id: str,
        filename: str,
        payload: bytes,
        content_type: str = "image/png",
    ) -> pb.SessionImage:
        """Client-stream a single image."""
        await self.connect()

        async def chunks() -> AsyncIterator[pb.ImageChunk]:
            yield pb.ImageChunk(
                session_id=session_id,
                filename=filename,
                content_type=content_type,
                data=payload,
            )

        response = await self._require_stub().UploadImage(chunks(), metadata=self._metadata())
        return cast(pb.SessionImage, response.image)
