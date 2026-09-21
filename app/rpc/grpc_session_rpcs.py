"""Session CRUD RPCs for the gRPC SessionService servicer."""

from grpc.aio import ServicerContext

from app.models import SessionCreate
from app.pb import session_service_pb2 as pb
from app.rpc.grpc_codec import (
    as_uuid,
    camera_caps,
    phone_caps,
    phone_info,
    session_to_pb,
    struct_to_dict,
)
from app.rpc.grpc_rpc import run_unary
from app.rpc.grpc_update import update_patch
from app.sessions.auth import Principal
from app.sessions.service import SessionService


class SessionRpcMixin:
    """Create/get/update/delete/list session RPCs."""

    _service: SessionService

    async def CreateSession(
        self,
        request: pb.CreateSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Create a session from protobuf device payloads."""

        async def work(principal: Principal | None) -> pb.SessionResponse:
            payload = SessionCreate(
                session_name=request.session_name,
                phone_info=phone_info(request.phone_info),
                phone_capabilities=phone_caps(request.phone_capabilities),
                camera_capabilities=camera_caps(request.camera_capabilities),
                extra_metadata=struct_to_dict(request.metadata),
            )
            session = await self._service.create_session(payload, principal)
            return pb.SessionResponse(session=session_to_pb(session))

        return await run_unary(context, self._service, work)

    async def GetSession(
        self,
        request: pb.GetSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Fetch a session by UUID string."""

        async def work(principal: Principal | None) -> pb.SessionResponse:
            session = await self._service.get_session(
                as_uuid(request.session_id, context),
                principal,
            )
            return pb.SessionResponse(session=session_to_pb(session))

        return await run_unary(context, self._service, work)

    async def UpdateSession(
        self,
        request: pb.UpdateSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Patch name, status, and/or metadata."""

        async def work(principal: Principal | None) -> pb.SessionResponse:
            session = await self._service.update_session(
                as_uuid(request.session_id, context),
                update_patch(request),
                principal,
            )
            return pb.SessionResponse(session=session_to_pb(session))

        return await run_unary(context, self._service, work)

    async def DeleteSession(
        self,
        request: pb.DeleteSessionRequest,
        context: ServicerContext,
    ) -> pb.DeleteSessionResponse:
        """Delete a session and unreferenced blobs."""

        async def work(principal: Principal | None) -> pb.DeleteSessionResponse:
            await self._service.delete_session(as_uuid(request.session_id, context), principal)
            return pb.DeleteSessionResponse(deleted=True)

        return await run_unary(context, self._service, work)

    async def ListSessions(
        self,
        request: pb.ListSessionsRequest,
        context: ServicerContext,
    ) -> pb.SessionListResponse:
        """List sessions with a cursor."""

        async def work(principal: Principal | None) -> pb.SessionListResponse:
            page = await self._service.list_sessions(
                limit=request.limit or None,
                cursor=request.cursor or None,
                principal=principal,
            )
            return pb.SessionListResponse(
                sessions=[session_to_pb(item) for item in page.items],
                next_cursor=page.next_cursor or "",
            )

        return await run_unary(context, self._service, work)
