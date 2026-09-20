"""Client-stream assembly for a single gRPC image upload."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from grpc.aio import ServicerContext

from app.exceptions import EmptyImageError, ImageTooLargeError
from app.grpc_errors import abort_rpc
from app.grpc_single_fill import collect_single
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.spool import SpoolWriter


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
    except (ImageTooLargeError, EmptyImageError) as exc:
        await abort_rpc(context, exc)
    except Exception:
        await writer.abort()
        raise
