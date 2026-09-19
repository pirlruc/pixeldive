"""Client-stream assembly for a single gRPC image upload."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import grpc
from grpc.aio import ServicerContext

from app.grpc_codec import as_uuid
from app.metadata import parse_metadata_json
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb


async def assemble_single(
    chunks: AsyncIterator[pb.ImageChunk],
    context: ServicerContext,
    *,
    max_bytes: int,
) -> tuple[uuid.UUID, ImageUpload]:
    """Collect a client-streamed image into one ImageUpload."""
    session_id: uuid.UUID | None = None
    filename = "upload.bin"
    content_type = "application/octet-stream"
    metadata: dict[str, Any] = {}
    buffer = bytearray()
    async for chunk in chunks:
        if session_id is None:
            if not chunk.session_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id is required")
            session_id = as_uuid(chunk.session_id, context)
            filename = chunk.filename or filename
            content_type = chunk.content_type or content_type
            metadata = parse_metadata_json(chunk.metadata_json or None)
        buffer.extend(chunk.data)
        if len(buffer) > max_bytes:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "image exceeds max_image_bytes")
    if session_id is None:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "empty image stream")
        raise RuntimeError("unreachable")
    upload = ImageUpload(
        filename=filename,
        content_type=content_type,
        payload=bytes(buffer),
        extra_metadata=metadata,
    )
    return session_id, upload
