"""Atomic writes into a local content-addressed blob store."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

import aiofiles
import aiofiles.os

from app.hash_keys import object_key, sha256_hex
from app.io_sizes import IO_CHUNK_BYTES


async def commit_tmp(tmp_path: Path, destination: Path) -> None:
    """Replace destination with tmp, cleaning up on races."""
    try:
        await aiofiles.os.replace(tmp_path, destination)
    except FileExistsError:
        await aiofiles.os.remove(tmp_path)
        if not await aiofiles.os.path.isfile(destination):
            raise
    except FileNotFoundError:
        if not await aiofiles.os.path.isfile(destination):
            raise


async def save_atomic(
    contained: Callable[[str], Path],
    key: str,
    write_tmp: Callable[[Path], Awaitable[None]],
) -> str:
    """Write ``key`` via a tmp file, skipping when the destination exists."""
    destination = contained(key)
    await aiofiles.os.makedirs(destination.parent, exist_ok=True)
    if await aiofiles.os.path.isfile(destination):
        return key
    tmp_path = destination.parent / f".{uuid.uuid4().hex}.tmp"
    await write_tmp(tmp_path)
    await commit_tmp(tmp_path, destination)
    return key


async def save_payload(
    contained: Callable[[str], Path],
    payload: bytes,
    content_type: str,
) -> str:
    """Write payload atomically; skip the write when the hash path exists."""

    async def write_tmp(tmp_path: Path) -> None:
        async with aiofiles.open(tmp_path, "wb") as handle:
            await handle.write(payload)

    return await save_atomic(contained, object_key(sha256_hex(payload), content_type), write_tmp)


async def save_spool_file(
    contained: Callable[[str], Path],
    source: Path,
    digest_hex: str,
    content_type: str,
) -> str:
    """Copy a spool file into the content-addressed layout."""

    async def write_tmp(tmp_path: Path) -> None:
        async with aiofiles.open(source, "rb") as src, aiofiles.open(tmp_path, "wb") as dst:
            while True:
                chunk = await src.read(IO_CHUNK_BYTES)
                if not chunk:
                    break
                await dst.write(chunk)

    return await save_atomic(contained, object_key(digest_hex, content_type), write_tmp)
