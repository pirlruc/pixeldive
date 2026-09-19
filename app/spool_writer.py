"""Incremental hashed writer for upload spools (PERF-001)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from app.exceptions import EmptyImageError, ImageTooLargeError
from app.spool_file import Spool


class SpoolWriter:
    """Incrementally hash and write chunks, aborting past ``max_bytes``."""

    def __init__(self, directory: Path, max_bytes: int) -> None:
        """Create a unique ``.part`` path under ``directory``."""
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{uuid.uuid4().hex}.part"
        self.max_bytes = max_bytes
        self.size = 0
        self.hasher = hashlib.sha256()
        self._handle: Any = None

    async def start(self) -> None:
        """Open the spool file for writing."""
        self._handle = await aiofiles.open(self.path, "wb")

    async def feed(self, chunk: bytes) -> None:
        """Append ``chunk`` or raise if the size ceiling is exceeded."""
        if not chunk:
            return
        self.size += len(chunk)
        if self.size > self.max_bytes:
            await self.abort()
            raise ImageTooLargeError(f"image exceeds max_image_bytes={self.max_bytes}")
        self.hasher.update(chunk)
        if self._handle is None:
            await self.start()
        assert self._handle is not None
        await self._handle.write(chunk)

    async def finish(self) -> Spool:
        """Close the file and return the spool, rejecting empty payloads."""
        if self._handle is not None:
            await self._handle.close()
            self._handle = None
        if self.size == 0:
            await self.abort()
            raise EmptyImageError("image payload is empty")
        return Spool(self.path, self.hasher.hexdigest(), self.size)

    async def abort(self) -> None:
        """Close and delete a partial spool."""
        if self._handle is not None:
            await self._handle.close()
            self._handle = None
        try:
            await aiofiles.os.remove(self.path)
        except FileNotFoundError:
            return
