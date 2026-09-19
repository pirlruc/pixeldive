"""Session CRUD RPCs for the gRPC SessionService servicer."""

from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.auth import Principal, authenticate, metadata_authorization
from app.exceptions import SessionServiceError
from app.grpc_codec import (
    as_uuid,
    camera_caps,
    phone_caps,
    phone_info,
    session_to_pb,
    struct_to_dict,
)
from app.grpc_errors import abort_rpc
from app.grpc_update import update_patch
from app.models import SessionCreate
from app.pb import session_service_pb2 as pb
from app.service import SessionService


def rpc_principal(context: ServicerContext, service: SessionService) -> Principal | None:
    """Resolve the caller from gRPC metadata."""
    header = metadata_authorization(tuple(context.invocation_metadata()))
    return authenticate(header, service._settings)


class SessionRpcMixin:
    """Create/get/update/delete/list session RPCs."""

    _service: SessionService

    async def CreateSession(
        self,
        request: pb.CreateSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Create a session from protobuf device payloads."""
        try:
            principal = rpc_principal(context, self._service)
            payload = SessionCreate(
                session_name=request.session_name,
                phone_info=phone_info(request.phone_info),
                phone_capabilities=phone_caps(request.phone_capabilities),
                camera_capabilities=camera_caps(request.camera_capabilities),
                extra_metadata=struct_to_dict(request.metadata),
            )
            session = await self._service.create_session(payload, principal)
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.SessionResponse(session=session_to_pb(session))

    async def GetSession(
        self,
        request: pb.GetSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Fetch a session by UUID string."""
        try:
            principal = rpc_principal(context, self._service)
            session = await self._service.get_session(
                as_uuid(request.session_id, context),
                principal,
            )
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.SessionResponse(session=session_to_pb(session))

    async def UpdateSession(
        self,
        request: pb.UpdateSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Patch name, status, and/or metadata."""
        try:
            principal = rpc_principal(context, self._service)
            session = await self._service.update_session(
                as_uuid(request.session_id, context),
                update_patch(request),
                principal,
            )
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.SessionResponse(session=session_to_pb(session))

    async def DeleteSession(
        self,
        request: pb.DeleteSessionRequest,
        context: ServicerContext,
    ) -> pb.DeleteSessionResponse:
        """Delete a session and unreferenced blobs."""
        try:
            principal = rpc_principal(context, self._service)
            await self._service.delete_session(as_uuid(request.session_id, context), principal)
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.DeleteSessionResponse(deleted=True)

    async def ListSessions(
        self,
        request: pb.ListSessionsRequest,
        context: ServicerContext,
    ) -> pb.SessionListResponse:
        """List sessions with a cursor."""
        try:
            principal = rpc_principal(context, self._service)
            page = await self._service.list_sessions(
                limit=request.limit or None,
                cursor=request.cursor or None,
                principal=principal,
            )
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.SessionListResponse(
            sessions=[session_to_pb(item) for item in page.items],
            next_cursor=page.next_cursor or "",
        )
