"""Async filesystem helpers shared by local storage and upload spools."""

from pathlib import Path

import aiofiles.os


async def unlink_missing(path: Path | str) -> None:
    """Remove ``path``; ignore if it is already gone."""
    try:
        await aiofiles.os.remove(path)
    except FileNotFoundError:
        return
