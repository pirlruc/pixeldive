"""Cursor paging helpers for list endpoints (API-002, PERF-001)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.cursors import decode_cursor, encode_cursor

__all__ = ["Page", "clamp_limit", "decode_cursor", "encode_cursor", "next_cursor"]


@dataclass(frozen=True, slots=True)
class Page[T]:
    """A page of rows plus an opaque next-page cursor."""

    items: list[T]
    next_cursor: str | None


def clamp_limit(limit: int | None, default: int, maximum: int) -> int:
    """Return a positive page size no larger than ``maximum``."""
    if limit is None or limit <= 0:
        return default
    return min(limit, maximum)


def next_cursor[T](
    rows: list[T],
    limit: int,
    stamp_of: Callable[[T], datetime],
    id_of: Callable[[T], uuid.UUID],
) -> tuple[list[T], str | None]:
    """Trim a ``limit+1`` fetch and encode a cursor from the last kept row."""
    if len(rows) <= limit:
        return rows, None
    kept = rows[:limit]
    last = kept[-1]
    return kept, encode_cursor(stamp_of(last), id_of(last))
