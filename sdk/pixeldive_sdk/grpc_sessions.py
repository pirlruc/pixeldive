"""Session RPCs for ``GrpcClient`` (API-003)."""

from __future__ import annotations

from typing import Any, cast

from app.pb import session_service_pb2 as pb
from pixeldive_sdk.grpc_host import GrpcHostMixin
from pixeldive_sdk.grpc_mapping import create_session_request, update_session_request
from pixeldive_sdk.ids import resource_id
from pixeldive_sdk.samples import sample_session_payload


class GrpcSessionCallsMixin(GrpcHostMixin):
    """Session CRUD RPCs that require an open stub."""

    async def create_session(self, payload: dict[str, Any] | None = None) -> pb.Session:
        """Create a session from a REST-shaped dict (defaults to the demo payload)."""
        body = payload or sample_session_payload()
        response = await self._unary("CreateSession", create_session_request(body))
        return cast(pb.Session, response.session)

    async def get_session(self, session_id: str) -> pb.Session:
        """Fetch a session by UUID."""
        response = await self._unary(
            "GetSession",
            pb.GetSessionRequest(session_id=resource_id(session_id)),
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
        response = await self._unary(
            "UpdateSession",
            update_session_request(resource_id(session_id), payload, merge_metadata=merge_metadata),
        )
        return cast(pb.Session, response.session)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and unreferenced blobs."""
        await self._unary(
            "DeleteSession",
            pb.DeleteSessionRequest(session_id=resource_id(session_id)),
        )

    async def list_sessions(self, *, limit: int = 50, cursor: str = "") -> pb.SessionListResponse:
        """List sessions with a cursor."""
        response = await self._unary(
            "ListSessions",
            pb.ListSessionsRequest(limit=limit, cursor=cursor),
        )
        return cast(pb.SessionListResponse, response)
