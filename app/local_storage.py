"""Deduplicating SHA-256 layout on the local filesystem."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
import aiofiles.os

from app.local_listing import file_age_seconds, list_local_blobs
from app.local_write import save_payload, save_spool_file


class LocalFilesystemStorage:
    """Deduplicating SHA-256 layout under ``root``."""

    def __init__(self, root: Path) -> None:
        """Create the backend rooted at ``root``."""
        self._root = root.resolve()

    def _contained(self, storage_path: str) -> Path:
        """Resolve ``storage_path`` and reject keys that escape ``root``."""
        candidate = (self._root / storage_path).resolve()
        if not candidate.is_relative_to(self._root):
            raise FileNotFoundError(storage_path)
        return candidate

    async def save(self, payload: bytes, content_type: str) -> str:
        """Write payload atomically; skip the write when the hash path exists."""
        return await save_payload(self._contained, payload, content_type)

    async def save_file(self, source: Path, digest_hex: str, content_type: str) -> str:
        """Copy a spool file into the content-addressed layout."""
        return await save_spool_file(self._contained, source, digest_hex, content_type)

    async def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Yield local file chunks."""
        async with aiofiles.open(self._contained(storage_path), "rb") as handle:
            while True:
                chunk = await handle.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def delete(self, storage_path: str) -> None:
        """Unlink the file; ignore if already gone."""
        try:
            await aiofiles.os.remove(self._contained(storage_path))
        except FileNotFoundError:
            return

    async def exists(self, storage_path: str) -> bool:
        """Return True when the local file is present."""
        try:
            return await aiofiles.os.path.isfile(self._contained(storage_path))
        except FileNotFoundError:
            return False

    async def list_blobs(self) -> list[tuple[str, float]]:
        """Walk the root and return relative keys with mtimes (skip tmp/spool)."""
        return list_local_blobs(self._root)

    async def age_seconds(self, storage_path: str) -> float:
        """Return file age; missing files are treated as age 0."""
        try:
            return await file_age_seconds(self._contained(storage_path))
        except FileNotFoundError:
            return 0.0
