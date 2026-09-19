"""Client-stream assembly for a gRPC batch image upload."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import grpc
from grpc.aio import ServicerContext

from app.exceptions import EmptyImageError, ImageTooLargeError
from app.grpc_batch_ingest import ingest_batch_chunk
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.spool import SpoolWriter


async def abort_pending(pending: dict[int, dict[str, Any]]) -> None:
    """Delete partial spools for images that never completed."""
    for slot in pending.values():
        writer: SpoolWriter = slot["writer"]
        await writer.abort()


async def assemble_batch(
    chunks: AsyncIterator[pb.BatchImageChunk],
    context: ServicerContext,
    *,
    max_bytes: int,
    max_images: int,
    spool_dir: Path,
) -> tuple[uuid.UUID, list[ImageUpload]]:
    """Collect a client-streamed batch into ImageUpload values."""
    session_id: uuid.UUID | None = None
    pending: dict[int, dict[str, Any]] = {}
    completed: list[ImageUpload] = []
    try:
        async for chunk in chunks:
            session_id = await ingest_batch_chunk(
                chunk,
                session_id=session_id,
                pending=pending,
                completed=completed,
                context=context,
                max_bytes=max_bytes,
                max_images=max_images,
                spool_dir=spool_dir,
            )
    except (ImageTooLargeError, EmptyImageError) as exc:
        await abort_pending(pending)
        await abort_limit(context, exc)
        raise
    except Exception:
        await abort_pending(pending)
        raise
    return await finish_batch(session_id, pending, completed, context)


async def abort_limit(context: ServicerContext, exc: BaseException) -> None:
    """Map spool errors onto gRPC INVALID_ARGUMENT."""
    message = (
        "image exceeds max_image_bytes"
        if isinstance(exc, ImageTooLargeError)
        else "empty image stream"
    )
    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, message)


async def finish_batch(
    session_id: uuid.UUID | None,
    pending: dict[int, dict[str, Any]],
    completed: list[ImageUpload],
    context: ServicerContext,
) -> tuple[uuid.UUID, list[ImageUpload]]:
    """Reject empty or partial batches after the stream ends."""
    if session_id is None:
        await abort_pending(pending)
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "empty batch stream")
        raise RuntimeError("unreachable")  # pragma: no cover
    if pending:
        await abort_pending(pending)
        await context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            "batch stream ended with partial image",
        )
        raise RuntimeError("unreachable")  # pragma: no cover
    return session_id, completed
