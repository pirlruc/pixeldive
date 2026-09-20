"""Session RPCs for ``GrpcClient`` (API-003)."""

from __future__ import annotations

from typing import Any, cast

from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_mapping import create_session_request, update_session_request
from pixeldive_sdk.ids import resource_id
from pixeldive_sdk.samples import sample_session_payload


class GrpcSessionCallsMixin:
    """Session CRUD RPCs that require an open stub."""

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

    async def get_session(self, session_id: str) -> pb.Session:
        """Fetch a session by UUID."""
        await self.connect()
        response = await self._require_stub().GetSession(
            pb.GetSessionRequest(session_id=resource_id(session_id)),
            metadata=self._metadata(),
        )
        return cast(pb.Session, response.session)

    async def update_session(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        merge_metadata: bool = False,
    ) -> pb.Session:
        """Patch name, status, and/or metadata."""
        await self.connect()
        response = await self._require_stub().UpdateSession(
            update_session_request(resource_id(session_id), payload, merge_metadata=merge_metadata),
            metadata=self._metadata(),
        )
        return cast(pb.Session, response.session)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and unreferenced blobs."""
        await self.connect()
        await self._require_stub().DeleteSession(
            pb.DeleteSessionRequest(session_id=resource_id(session_id)),
            metadata=self._metadata(),
        )

    async def list_sessions(self, *, limit: int = 50, cursor: str = "") -> pb.SessionListResponse:
        """List sessions with a cursor."""
        await self.connect()
        response = await self._require_stub().ListSessions(
            pb.ListSessionsRequest(limit=limit, cursor=cursor),
            metadata=self._metadata(),
        )
        return cast(pb.SessionListResponse, response)
