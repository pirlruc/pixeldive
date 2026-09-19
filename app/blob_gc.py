"""Race-aware blob garbage collection and orphan sweeping (DATA-002)."""

from __future__ import annotations

import time
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from app.models import SessionImage
from app.storage import StorageBackend


async def referenced_paths(
    factory: async_sessionmaker[AsyncSession],
    paths: Sequence[str],
) -> set[str]:
    """Return the subset of ``paths`` still referenced by image rows."""
    unique = list(dict.fromkeys(paths))
    if not unique:
        return set()
    async with factory() as db:
        statement = (
            select(col(SessionImage.storage_path))
            .where(col(SessionImage.storage_path).in_(unique))
            .distinct()
        )
        return set((await db.execute(statement)).scalars().all())


async def all_referenced_paths(factory: async_sessionmaker[AsyncSession]) -> set[str]:
    """Return every storage_path currently referenced."""
    async with factory() as db:
        statement = select(col(SessionImage.storage_path)).distinct()
        return set((await db.execute(statement)).scalars().all())


async def gc_unreferenced(
    factory: async_sessionmaker[AsyncSession],
    storage: StorageBackend,
    paths: Sequence[str],
    *,
    min_age_seconds: float,
) -> None:
    """Delete blobs with zero remaining refs, re-checking immediately before unlink.

    ``min_age_seconds`` skips newly written objects so a concurrent upload of the
    same digest can insert its row before a sweeper reclaims the file.
    """
    unique = list(dict.fromkeys(paths))
    if not unique:
        return
    still_used = await referenced_paths(factory, unique)
    for path in unique:
        if path in still_used:
            continue
        if min_age_seconds > 0:
            age = await storage.age_seconds(path)
            if age < min_age_seconds:
                continue
        if path in await referenced_paths(factory, [path]):
            continue
        await storage.delete(path)


async def sweep_orphans(
    factory: async_sessionmaker[AsyncSession],
    storage: StorageBackend,
    *,
    min_age_seconds: float,
) -> int:
    """Delete unreferenced blobs older than ``min_age_seconds``. Return count."""
    blobs = await storage.list_blobs()
    if not blobs:
        return 0
    used = await all_referenced_paths(factory)
    deleted = 0
    now = time.time()
    for key, mtime in blobs:
        if key in used:
            continue
        if now - mtime < min_age_seconds:
            continue
        if key in await referenced_paths(factory, [key]):
            continue
        await storage.delete(key)
        deleted += 1
    return deleted
