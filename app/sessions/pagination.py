"""Cursor paging helpers for list endpoints (API-002, PERF-001)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_

from app.sessions.cursors import decode_cursor, encode_cursor

__all__ = [
    "Page",
    "clamp_limit",
    "cursor_predicate",
    "decode_cursor",
    "encode_cursor",
    "next_cursor",
]


@dataclass(frozen=True, slots=True)
class Page[T]:
    """A page of rows plus an opaque next-page cursor."""

    items: list[T]
    next_cursor: str | None


def cursor_predicate(
    stamp_col: Any,
    id_col: Any,
    cursor: str | None,
    *,
    descending: bool,
) -> Any | None:
    """Return a WHERE clause that continues after ``cursor``, or ``None``."""
    if not cursor:
        return None
    stamp, item_id = decode_cursor(cursor)
    if descending:
        return or_(stamp_col < stamp, and_(stamp_col == stamp, id_col < item_id))
    return or_(stamp_col > stamp, and_(stamp_col == stamp, id_col > item_id))


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
