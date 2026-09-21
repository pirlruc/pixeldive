"""Client-stream assembly for a single gRPC image upload."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from grpc.aio import ServicerContext

from app.blobs.spool import SpoolWriter
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.rpc.grpc_errors import rethrow_ingest
from app.rpc.grpc_single_fill import collect_single


async def assemble_single(
    chunks: AsyncIterator[pb.ImageChunk],
    context: ServicerContext,
    *,
    max_bytes: int,
    spool_dir: Path,
) -> tuple[uuid.UUID, ImageUpload]:
    """Collect a client-streamed image into one spooled ImageUpload."""
    writer = SpoolWriter(spool_dir, max_bytes)
    await writer.start()
    try:
        return await collect_single(chunks, context, writer)
    except Exception as exc:
        await rethrow_ingest(context, exc, writer.abort)
