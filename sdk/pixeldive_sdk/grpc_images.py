"""Image RPCs for ``GrpcClient`` (API-003, PERF-004)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any, cast

from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.chunking import DEFAULT_CHUNK_BYTES, iter_bytes, iter_path
from pixeldive_sdk.grpc_iter import batch_image_chunks, single_image_chunks
from pixeldive_sdk.ids import resource_id


class GrpcImageCallsMixin:
    """Image upload/list/download RPCs that require an open stub."""

    async def connect(self) -> None:
        """Open the channel; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _metadata(self) -> list[tuple[str, str]]:
        """Invocation metadata; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _require_stub(self) -> pb_grpc.SessionServiceStub:
        """Return the stub; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    async def upload_image(
        self,
        session_id: str,
        filename: str,
        payload: bytes,
        content_type: str = "image/png",
        *,
        chunk_size: int = DEFAULT_CHUNK_BYTES,
    ) -> pb.SessionImage:
        """Client-stream a single image, splitting large payloads into chunks."""
        return await self._upload_chunks(
            resource_id(session_id),
            filename,
            content_type,
            iter_bytes(payload, chunk_size),
        )

    async def upload_image_from_path(
        self,
        session_id: str,
        path: str | Path,
        *,
        filename: str | None = None,
        content_type: str = "image/png",
        chunk_size: int = DEFAULT_CHUNK_BYTES,
    ) -> pb.SessionImage:
        """Client-stream a file from disk without buffering the whole payload."""
        source = Path(path)
        return await self._upload_chunks(
            resource_id(session_id),
            filename or source.name,
            content_type,
            iter_path(source, chunk_size),
        )

    async def upload_images_batch(
        self,
        session_id: str,
        items: Sequence[tuple[str, bytes, str]],
        *,
        chunk_size: int = DEFAULT_CHUNK_BYTES,
    ) -> list[pb.SessionImage]:
        """Client-stream a batch of in-memory images."""
        await self.connect()

        async def chunks() -> AsyncIterator[pb.BatchImageChunk]:
            sid = resource_id(session_id)
            for index, (filename, payload, content_type) in enumerate(items):
                async for chunk in batch_image_chunks(
                    sid,
                    index,
                    filename,
                    content_type,
                    iter_bytes(payload, chunk_size),
                ):
                    yield chunk

        response = await self._require_stub().UploadImagesBatch(
            chunks(),
            metadata=self._metadata(),
        )
        return list(response.images)

    async def list_images(
        self,
        session_id: str,
        *,
        limit: int = 50,
        cursor: str = "",
    ) -> pb.ImageListResponse:
        """List image metadata for a session."""
        await self.connect()
        response = await self._require_stub().ListSessionImages(
            pb.ListImagesRequest(session_id=resource_id(session_id), limit=limit, cursor=cursor),
            metadata=self._metadata(),
        )
        return cast(pb.ImageListResponse, response)

    async def download_image(self, session_id: str, image_id: str) -> AsyncIterator[bytes]:
        """Server-stream image bytes."""
        await self.connect()
        call = self._require_stub().DownloadImage(
            pb.DownloadImageRequest(
                session_id=resource_id(session_id),
                image_id=resource_id(image_id),
            ),
            metadata=self._metadata(),
        )
        async for chunk in call:
            yield chunk.data

    async def _upload_chunks(
        self,
        session_id: str,
        filename: str,
        content_type: str,
        pieces: Any,
    ) -> pb.SessionImage:
        """Send ImageChunk messages for ``pieces``."""
        await self.connect()
        response = await self._require_stub().UploadImage(
            single_image_chunks(session_id, filename, content_type, pieces),
            metadata=self._metadata(),
        )
        return cast(pb.SessionImage, response.image)
