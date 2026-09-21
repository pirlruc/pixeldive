"""Per-chunk helpers for a gRPC batch image upload."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import grpc
from grpc.aio import ServicerContext

from app.grpc_batch_slots import apply_batch_chunk, new_batch_slot, upload_from_slot
from app.grpc_codec import as_uuid
from app.grpc_errors import require_session_id
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb


async def ingest_batch_chunk(
    chunk: pb.BatchImageChunk,
    *,
    session_id: uuid.UUID | None,
    pending: dict[int, dict[str, Any]],
    completed: list[ImageUpload],
    context: ServicerContext,
    max_bytes: int,
    max_images: int,
    spool_dir: Path,
) -> uuid.UUID:
    """Apply one batch chunk and return the resolved session id."""
    resolved = await batch_session_id(chunk, session_id, context)
    if chunk.image_index not in pending and (len(pending) + len(completed)) >= max_images:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "batch exceeds max_batch_images")
    slot = pending.get(chunk.image_index)
    if slot is None:
        slot = await new_batch_slot(chunk, spool_dir, max_bytes)
        pending[chunk.image_index] = slot
    await apply_batch_chunk(slot, chunk)
    if chunk.end_of_image:
        completed.append(await upload_from_slot(slot))
        del pending[chunk.image_index]
    return resolved


async def batch_session_id(
    chunk: pb.BatchImageChunk,
    session_id: uuid.UUID | None,
    context: ServicerContext,
) -> uuid.UUID:
    """Require session_id on the first chunk."""
    if session_id is not None:
        return session_id
    await require_session_id(chunk.session_id, context)
    return as_uuid(chunk.session_id, context)
