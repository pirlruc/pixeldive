"""Stream an upload to a temp file while hashing incrementally (PERF-001)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from app.spool_file import Spool
from app.spool_writer import SpoolWriter

__all__ = ["Spool", "SpoolWriter", "spool_chunks"]


async def spool_chunks(
    chunks: AsyncIterator[bytes],
    directory: Path,
    max_bytes: int,
) -> Spool:
    """Write an async byte stream to a spool file."""
    writer = SpoolWriter(directory, max_bytes)
    await writer.start()
    try:
        async for chunk in chunks:
            await writer.feed(chunk)
        return await writer.finish()
    except Exception:
        await writer.abort()
        raise
