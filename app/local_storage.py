"""Deduplicating SHA-256 layout on the local filesystem."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
import aiofiles.os

from app.hash_keys import object_key, sha256_hex


class LocalFilesystemStorage:
    """Deduplicating SHA-256 layout under ``root``."""

    def __init__(self, root: Path) -> None:
        """Create the backend rooted at ``root``."""
        self._root = root

    async def save(self, payload: bytes, content_type: str) -> str:
        """Write payload atomically; skip the write when the hash path exists."""
        key = object_key(sha256_hex(payload), content_type)
        destination = self._root / key
        await aiofiles.os.makedirs(destination.parent, exist_ok=True)
        if destination.exists():
            return key
        tmp_path = destination.parent / f".{uuid.uuid4().hex}.tmp"
        async with aiofiles.open(tmp_path, "wb") as handle:
            await handle.write(payload)
        try:
            await aiofiles.os.replace(tmp_path, destination)
        except FileExistsError:
            await aiofiles.os.remove(tmp_path)
        except FileNotFoundError:
            if not destination.exists():
                raise
        return key

    async def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Yield local file chunks."""
        async with aiofiles.open(self._root / storage_path, "rb") as handle:
            while True:
                chunk = await handle.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def delete(self, storage_path: str) -> None:
        """Unlink the file; ignore if already gone."""
        path = self._root / storage_path
        try:
            await aiofiles.os.remove(path)
        except FileNotFoundError:
            return

    async def exists(self, storage_path: str) -> bool:
        """Return True when the local file is present."""
        return (self._root / storage_path).is_file()
