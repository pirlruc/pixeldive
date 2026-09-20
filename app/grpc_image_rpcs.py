"""Image upload/list/download RPCs for the gRPC SessionService servicer."""

from collections.abc import AsyncIterator

from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.auth import Principal
from app.exceptions import SessionServiceError
from app.grpc_codec import as_uuid, image_to_pb
from app.grpc_errors import abort_rpc
from app.grpc_rpc import rpc_principal, run_unary
from app.grpc_streams import assemble_batch, assemble_single
from app.pb import session_service_pb2 as pb
from app.service import SessionService


class ImageRpcMixin:
    """Upload, list, and download image RPCs."""

    _service: SessionService

    async def UploadImage(
        self,
        request_iterator: AsyncIterator[pb.ImageChunk],
        context: ServicerContext,
    ) -> pb.ImageUploadResponse:
        """Client-stream a single image."""

        async def work(principal: Principal | None) -> pb.ImageUploadResponse:
            session_id, upload = await assemble_single(
                request_iterator,
                context,
                max_bytes=self._service._settings.max_image_bytes,
                spool_dir=self._service._settings.spool_dir(),
            )
            image = await self._service.add_image(session_id, upload, principal)
            return pb.ImageUploadResponse(image=image_to_pb(image))

        return await run_unary(context, self._service, work)

    async def UploadImagesBatch(
        self,
        request_iterator: AsyncIterator[pb.BatchImageChunk],
        context: ServicerContext,
    ) -> pb.BatchUploadResponse:
        """Client-stream a batch of images."""

        async def work(principal: Principal | None) -> pb.BatchUploadResponse:
            session_id, uploads = await assemble_batch(
                request_iterator,
                context,
                max_bytes=self._service._settings.max_image_bytes,
                max_images=self._service._settings.max_batch_images,
                spool_dir=self._service._settings.spool_dir(),
            )
            images = await self._service.add_images_batch(session_id, uploads, principal)
            return pb.BatchUploadResponse(images=[image_to_pb(item) for item in images])

        return await run_unary(context, self._service, work)

    async def ListSessionImages(
        self,
        request: pb.ListImagesRequest,
        context: ServicerContext,
    ) -> pb.ImageListResponse:
        """List image metadata for a session."""

        async def work(principal: Principal | None) -> pb.ImageListResponse:
            page = await self._service.list_images(
                as_uuid(request.session_id, context),
                limit=request.limit or None,
                cursor=request.cursor or None,
                principal=principal,
            )
            return pb.ImageListResponse(
                images=[image_to_pb(item) for item in page.items],
                next_cursor=page.next_cursor or "",
            )

        return await run_unary(context, self._service, work)

    async def DownloadImage(
        self,
        request: pb.DownloadImageRequest,
        context: ServicerContext,
    ) -> AsyncIterator[pb.ImageChunk]:
        """Server-stream image bytes."""
        try:
            principal = rpc_principal(context, self._service)
            session_id = as_uuid(request.session_id, context)
            image_id = as_uuid(request.image_id, context)
            image = await self._service.get_image(session_id, image_id, principal)
            async for chunk in self._service.stream_image(
                session_id,
                image_id,
                principal,
                image=image,
            ):
                yield pb.ImageChunk(
                    session_id=str(session_id),
                    image_id=str(image_id),
                    filename=image.filename,
                    content_type=image.content_type,
                    data=chunk,
                )
        except (SessionServiceError, ValidationError) as exc:
            await abort_rpc(context, exc)
