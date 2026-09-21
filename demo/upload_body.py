"""Cap a demo multipart upload, spilling to disk only for the REST fallback."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

_CHUNK = 1024 * 1024
_DEFAULT_MAX = 32 * 1024 * 1024


def max_demo_upload_bytes() -> int:
    """Read ``DEMO_MAX_IMAGE_BYTES``, defaulting to 32 MiB."""
    raw = os.environ.get("DEMO_MAX_IMAGE_BYTES")
    if not raw:
        return _DEFAULT_MAX
    return int(raw)


def reject_over_cap(size: int, limit: int) -> None:
    """Raise HTTP 413 when ``size`` is past the demo cap."""
    if size > limit:
        raise HTTPException(status_code=413, detail="image exceeds demo max size")


async def read_capped_chunks(file: UploadFile) -> list[bytes]:
    """Read multipart pieces once, rejecting a body over the demo cap."""
    # Hold one chunk list, then stream those objects. Raising inside the gRPC
    # request iterator cancels the call instead of returning HTTP 413.
    limit = max_demo_upload_bytes()
    size = 0
    pieces: list[bytes] = []
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            return pieces
        size += len(chunk)
        reject_over_cap(size, limit)
        pieces.append(chunk)


async def write_upload(file: UploadFile) -> Path:
    """Copy ``file`` to a temp path, rejecting bodies over the demo cap."""
    limit = max_demo_upload_bytes()
    fd, name = tempfile.mkstemp(prefix="pixeldive-demo-", suffix=".part")
    path = Path(name)
    size = 0
    completed = False
    try:
        with os.fdopen(fd, "wb") as handle:
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                reject_over_cap(size, limit)
                handle.write(chunk)
        completed = True
        return path
    finally:
        if not completed:
            path.unlink(missing_ok=True)
