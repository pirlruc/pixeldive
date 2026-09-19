"""gRPC aio transport for SessionService (API-001)."""

from collections.abc import AsyncIterator

import grpc
from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.exceptions import SessionServiceError
from app.grpc_codec import (
    as_uuid,
    camera_caps,
    image_to_pb,
    phone_caps,
    phone_info,
    session_to_pb,
    struct_to_dict,
)
from app.grpc_errors import abort_rpc
from app.grpc_streams import assemble_batch, assemble_single
from app.models import SessionCreate, SessionUpdate
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.service import SessionService

# Re-export for tests that patch/import the abort helper.
_abort = abort_rpc


class SessionServicer(pb_grpc.SessionServiceServicer):
    """gRPC servicer that delegates to SessionService."""

    def __init__(self, service: SessionService) -> None:
        """Bind the shared business layer."""
        self._service = service

    async def CreateSession(
        self,
        request: pb.CreateSessionRequest,
        context: ServicerContext,
    ) -> pb.SessionResponse:
        """Create a session from protobuf device payloads."""
        try:
            payload = SessionCreate(
                session_name=request.session_name,
                phone_info=phone_info(request.phone_info),
                phone_capabilities=phone_caps(request.phone_capabilities),
                camera_capabilities=camera_caps(request.camera_capabilities),
                extra_metadata=struct_to_dict(request.metadata),
            )
            session = await self._service.create_session(payload)
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
            session = await self._service.get_session(as_uuid(request.session_id, context))
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
            patch = SessionUpdate(
                session_name=request.session_name if request.HasField("session_name") else None,
                status=request.status if request.HasField("status") else None,  # type: ignore[arg-type]
                extra_metadata=struct_to_dict(request.metadata) or None,
            )
            session = await self._service.update_session(
                as_uuid(request.session_id, context),
                patch,
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
            await self._service.delete_session(as_uuid(request.session_id, context))
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.DeleteSessionResponse(deleted=True)

    async def UploadImage(
        self,
        request_iterator: AsyncIterator[pb.ImageChunk],
        context: ServicerContext,
    ) -> pb.ImageUploadResponse:
        """Client-stream a single image."""
        try:
            session_id, upload = await assemble_single(request_iterator, context)
            image = await self._service.add_image(session_id, upload)
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.ImageUploadResponse(image=image_to_pb(image))

    async def UploadImagesBatch(
        self,
        request_iterator: AsyncIterator[pb.BatchImageChunk],
        context: ServicerContext,
    ) -> pb.BatchUploadResponse:
        """Client-stream a batch of images."""
        try:
            session_id, uploads = await assemble_batch(request_iterator, context)
            images = await self._service.add_images_batch(session_id, uploads)
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.BatchUploadResponse(images=[image_to_pb(item) for item in images])

    async def ListSessionImages(
        self,
        request: pb.ListImagesRequest,
        context: ServicerContext,
    ) -> pb.ImageListResponse:
        """List image metadata for a session."""
        try:
            images = await self._service.list_images(as_uuid(request.session_id, context))
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
        return pb.ImageListResponse(images=[image_to_pb(item) for item in images])

    async def DownloadImage(
        self,
        request: pb.DownloadImageRequest,
        context: ServicerContext,
    ) -> AsyncIterator[pb.ImageChunk]:
        """Server-stream image bytes."""
        try:
            session_id = as_uuid(request.session_id, context)
            image_id = as_uuid(request.image_id, context)
            image = await self._service.get_image(session_id, image_id)
            async for chunk in self._service.stream_image(session_id, image_id):
                yield pb.ImageChunk(
                    session_id=str(session_id),
                    image_id=str(image_id),
                    filename=image.filename,
                    content_type=image.content_type,
                    data=chunk,
                )
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)


async def start_grpc_server(
    service: SessionService,
    host: str,
    port: int,
) -> tuple[grpc.aio.Server, int]:
    """Start an aio gRPC server and return it with the bound port."""
    server = grpc.aio.server()
    pb_grpc.add_SessionServiceServicer_to_server(SessionServicer(service), server)
    bound_port = server.add_insecure_port(f"{host}:{port}")
    await server.start()
    return server, bound_port
