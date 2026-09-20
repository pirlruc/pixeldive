"""Split payloads into gRPC ImageChunk-sized windows (PERF-004)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

DEFAULT_CHUNK_BYTES = 256 * 1024


def iter_bytes(payload: bytes, chunk_size: int = DEFAULT_CHUNK_BYTES) -> Iterator[bytes]:
    """Yield successive slices of ``payload`` (empty payload yields once)."""
    size = max(chunk_size, 1)
    if not payload:
        yield payload
        return
    offset = 0
    while offset < len(payload):
        yield payload[offset : offset + size]
        offset += size


async def iter_path(path: Path, chunk_size: int = DEFAULT_CHUNK_BYTES) -> AsyncIterator[bytes]:
    """Yield file bytes without loading the whole file into memory."""
    size = max(chunk_size, 1)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(size)
            if not chunk:
                return
            yield chunk
