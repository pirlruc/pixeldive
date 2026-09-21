"""Read a client-streamed gRPC image into a spool writer."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import grpc
from grpc.aio import ServicerContext

from app.blobs.spool import SpoolWriter
from app.blobs.uploads import upload_from_spool
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.rpc.grpc_codec import as_uuid
from app.rpc.grpc_errors import require_session_id
from app.rpc.grpc_headers import chunk_headers


async def collect_single(
    chunks: AsyncIterator[pb.ImageChunk],
    context: ServicerContext,
    writer: SpoolWriter,
) -> tuple[uuid.UUID, ImageUpload]:
    """Read chunks into ``writer`` and return the finished upload."""
    session_id, filename, content_type, metadata = await fill_spool(chunks, context, writer)
    spool = await writer.finish()
    if session_id is None:
        await spool.delete()
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "empty image stream")
        raise RuntimeError("unreachable")  # pragma: no cover
    return session_id, upload_from_spool(filename, content_type, spool, metadata)


async def fill_spool(
    chunks: AsyncIterator[pb.ImageChunk],
    context: ServicerContext,
    writer: SpoolWriter,
) -> tuple[uuid.UUID | None, str, str, dict[str, Any]]:
    """Feed the stream and capture headers from the first chunk."""
    session_id: uuid.UUID | None = None
    filename = "upload.bin"
    content_type = "application/octet-stream"
    metadata: dict[str, Any] = {}
    async for chunk in chunks:
        if session_id is None:
            session_id, filename, content_type, metadata = await single_header(
                chunk,
                context,
                writer,
                filename,
                content_type,
            )
        await writer.feed(chunk.data)
    return session_id, filename, content_type, metadata


async def single_header(
    chunk: pb.ImageChunk,
    context: ServicerContext,
    writer: SpoolWriter,
    filename: str,
    content_type: str,
) -> tuple[uuid.UUID, str, str, dict[str, Any]]:
    """Parse session_id/filename/type/metadata from the first chunk."""
    await require_session_id(chunk.session_id, context, writer.abort)
    name, media_type, metadata = chunk_headers(
        chunk.filename,
        chunk.content_type,
        chunk.metadata_json,
    )
    return (
        as_uuid(chunk.session_id, context),
        name or filename,
        media_type or content_type,
        metadata,
    )
