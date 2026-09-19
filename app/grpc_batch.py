"""Client-stream assembly for a gRPC batch image upload."""

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


def new_batch_slot(chunk: pb.BatchImageChunk) -> dict[str, Any]:
    """Start a pending image accumulator from the first chunk of that index."""
    return {
        "filename": chunk.filename or "upload.bin",
        "content_type": chunk.content_type or "application/octet-stream",
        "metadata": parse_metadata_json(chunk.metadata_json or None),
        "buffer": bytearray(),
    }


def apply_batch_chunk(slot: dict[str, Any], chunk: pb.BatchImageChunk) -> None:
    """Merge filename/type/metadata/bytes into an accumulator slot."""
    if chunk.filename:
        slot["filename"] = chunk.filename
    if chunk.content_type:
        slot["content_type"] = chunk.content_type
    if chunk.metadata_json:
        slot["metadata"] = parse_metadata_json(chunk.metadata_json)
    slot["buffer"].extend(chunk.data)


def upload_from_slot(slot: dict[str, Any]) -> ImageUpload:
    """Convert an accumulator slot into an ImageUpload."""
    return ImageUpload(
        filename=slot["filename"],
        content_type=slot["content_type"],
        payload=bytes(slot["buffer"]),
        extra_metadata=slot["metadata"],
    )


async def assemble_batch(
    chunks: AsyncIterator[pb.BatchImageChunk],
    context: ServicerContext,
    *,
    max_bytes: int,
    max_images: int,
) -> tuple[uuid.UUID, list[ImageUpload]]:
    """Collect a client-streamed batch into ImageUpload values."""
    session_id: uuid.UUID | None = None
    pending: dict[int, dict[str, Any]] = {}
    completed: list[ImageUpload] = []
    async for chunk in chunks:
        if session_id is None:
            if not chunk.session_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id is required")
            session_id = as_uuid(chunk.session_id, context)
        if chunk.image_index not in pending and (len(pending) + len(completed)) >= max_images:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "batch exceeds max_batch_images")
        slot = pending.setdefault(chunk.image_index, new_batch_slot(chunk))
        apply_batch_chunk(slot, chunk)
        if len(slot["buffer"]) > max_bytes:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "image exceeds max_image_bytes")
        if chunk.end_of_image:
            completed.append(upload_from_slot(slot))
            del pending[chunk.image_index]
    if session_id is None:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "empty batch stream")
        raise RuntimeError("unreachable")
    if pending:
        await context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            "batch stream ended with partial image",
        )
    return session_id, completed
