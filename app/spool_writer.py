"""Incremental hashed writer for upload spools (PERF-001)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any, cast

import aiofiles

from app.empty_chunks import empty_run_exceeded
from app.exceptions import EmptyImageError, ImageTooLargeError
from app.fs_async import unlink_missing
from app.magic import HEADER_SIZE
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
        self.header = bytearray()
        self._handle: Any = None
        self._empty_run = 0

    async def start(self) -> None:
        """Open the spool file for writing."""
        self._handle = await aiofiles.open(self.path, "wb")

    async def _close(self) -> None:
        """Close the open handle if any."""
        if self._handle is None:
            return
        await self._handle.close()
        self._handle = None

    async def feed(self, chunk: bytes) -> None:
        """Append ``chunk`` or raise if the size ceiling is exceeded."""
        # Empty frames do not count toward max_image_bytes. A long run of them
        # is a stalled client, so the stream aborts instead of staying open.
        if not chunk:
            self._empty_run += 1
            if empty_run_exceeded(self._empty_run):
                await self.abort()
                raise EmptyImageError("too many empty upload chunks")
            return
        self._empty_run = 0
        self.size += len(chunk)
        if self.size > self.max_bytes:
            await self.abort()
            raise ImageTooLargeError(f"image exceeds max_image_bytes={self.max_bytes}")
        self.hasher.update(chunk)
        if len(self.header) < HEADER_SIZE:
            self.header.extend(chunk[: HEADER_SIZE - len(self.header)])
        if self._handle is None:
            await self.start()
        await cast(Any, self._handle).write(chunk)

    async def finish(self) -> Spool:
        """Close the file and return the spool, rejecting empty payloads."""
        await self._close()
        if self.size == 0:
            await self.abort()
            raise EmptyImageError("image payload is empty")
        return Spool(self.path, self.hasher.hexdigest(), self.size, bytes(self.header))

    async def abort(self) -> None:
        """Close and delete a partial spool."""
        await self._close()
        await unlink_missing(self.path)
