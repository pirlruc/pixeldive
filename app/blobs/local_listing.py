"""Walk a local content-addressed store, skipping tmp and spool files."""

from __future__ import annotations

import time
from pathlib import Path

import aiofiles.os


def list_local_blobs(root: Path) -> list[tuple[str, float]]:
    """Return relative keys with mtimes, ignoring dotted path parts."""
    blobs: list[tuple[str, float]] = []
    if not root.exists():
        return blobs
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        blobs.append((path.relative_to(root).as_posix(), path.stat().st_mtime))
    return blobs


async def file_age_seconds(path: Path) -> float:
    """Return file age; missing files are treated as age 0."""
    try:
        stat = await aiofiles.os.stat(path)
    except FileNotFoundError:
        return 0.0
    return max(0.0, time.time() - stat.st_mtime)
