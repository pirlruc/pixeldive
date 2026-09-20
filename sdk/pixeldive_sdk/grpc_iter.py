"""gRPC ImageChunk / BatchImageChunk iterators for streaming uploads."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from app.pb import session_service_pb2 as pb

BytePieces = AsyncIterator[bytes] | Iterator[bytes] | Any


async def ensure_async(pieces: BytePieces) -> AsyncIterator[bytes]:
    """Normalize a sync iterator or async iterator of bytes."""
    if hasattr(pieces, "__aiter__"):
        async for piece in pieces:
            yield piece
        return
    for piece in pieces:
        yield piece


async def single_image_chunks(
    session_id: str,
    filename: str,
    content_type: str,
    pieces: BytePieces,
) -> AsyncIterator[pb.ImageChunk]:
    """Yield ImageChunk messages, putting headers on the first frame."""
    first = True
    async for piece in ensure_async(pieces):
        if first:
            yield pb.ImageChunk(
                session_id=session_id,
                filename=filename,
                content_type=content_type,
                data=piece,
            )
            first = False
        else:
            yield pb.ImageChunk(data=piece)
    if first:
        yield pb.ImageChunk(
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            data=b"",
        )


async def batch_image_chunks(
    session_id: str,
    index: int,
    filename: str,
    content_type: str,
    pieces: BytePieces,
) -> AsyncIterator[pb.BatchImageChunk]:
    """Yield BatchImageChunk messages for one image, ending with end_of_image."""
    last: bytes | None = None
    first = True
    async for piece in ensure_async(pieces):
        if last is not None:
            yield _batch_frame(session_id, index, filename, content_type, last, first, False)
            first = False
        last = piece
    yield _batch_frame(session_id, index, filename, content_type, last or b"", first, True)


def _batch_frame(
    session_id: str,
    index: int,
    filename: str,
    content_type: str,
    data: bytes,
    first: bool,
    end: bool,
) -> pb.BatchImageChunk:
    """Build one batch frame, omitting headers after the first."""
    return pb.BatchImageChunk(
        session_id=session_id if first else "",
        image_index=index,
        filename=filename if first else "",
        content_type=content_type if first else "",
        data=data,
        end_of_image=end,
    )
