"""Per-image spool slots used while assembling a gRPC batch upload."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.grpc_headers import chunk_headers
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.spool import SpoolWriter
from app.uploads import upload_from_spool


async def new_batch_slot(
    chunk: pb.BatchImageChunk, spool_dir: Path, max_bytes: int
) -> dict[str, Any]:
    """Start a pending image accumulator from the first chunk of that index."""
    writer = SpoolWriter(spool_dir, max_bytes)
    await writer.start()
    filename, content_type, metadata = chunk_headers(
        chunk.filename,
        chunk.content_type,
        chunk.metadata_json,
    )
    return {
        "filename": filename,
        "content_type": content_type,
        "metadata": metadata,
        "writer": writer,
    }


async def apply_batch_chunk(slot: dict[str, Any], chunk: pb.BatchImageChunk) -> None:
    """Merge filename/type/metadata/bytes into an accumulator slot."""
    if chunk.filename or chunk.content_type or chunk.metadata_json:
        filename, content_type, metadata = chunk_headers(
            chunk.filename,
            chunk.content_type,
            chunk.metadata_json,
        )
        if chunk.filename:
            slot["filename"] = filename
        if chunk.content_type:
            slot["content_type"] = content_type
        if chunk.metadata_json:
            slot["metadata"] = metadata
    writer: SpoolWriter = slot["writer"]
    await writer.feed(chunk.data)


async def upload_from_slot(slot: dict[str, Any]) -> ImageUpload:
    """Convert an accumulator slot into an ImageUpload."""
    writer: SpoolWriter = slot["writer"]
    spool = await writer.finish()
    return upload_from_spool(slot["filename"], slot["content_type"], spool, slot["metadata"])
