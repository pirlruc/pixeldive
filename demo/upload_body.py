"""Spill a demo multipart upload to a capped temp file (PERF-006)."""

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
                if size > limit:
                    raise HTTPException(status_code=413, detail="image exceeds demo max size")
                handle.write(chunk)
        completed = True
        return path
    finally:
        if not completed:
            path.unlink(missing_ok=True)
