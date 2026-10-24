"""Pure helpers for the shared SQL quota table."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from app.exceptions import QuotaExceededError

_SELECT = "SELECT bytes_used, hits FROM tenant_quota WHERE scope = :scope"


@dataclass(frozen=True, slots=True)
class QuotaRow:
    """One locked ``tenant_quota`` row."""

    bytes_used: int
    hits: str


def dialect_name(database_url: str) -> str:
    """Return the lock dialect for ``database_url``."""
    if database_url.startswith("postgresql"):
        return "postgresql"
    return "other"


def lock_select(dialect: str) -> str:
    """Row-lock on PostgreSQL so two processes share one budget."""
    if dialect == "postgresql":
        return f"{_SELECT} FOR UPDATE"
    return _SELECT


def parse_hits(raw: str) -> list[float]:
    """Decode the JSON hit list stored on a tenant row."""
    loaded = json.loads(raw)
    if not isinstance(loaded, list):
        msg = "quota hits must be a list"
        raise ValueError(msg)
    return [float(item) for item in loaded]


def prune_hits(hits: list[float], now: float, window: float) -> list[float]:
    """Drop timestamps at or before the start of the window."""
    cutoff = now - window
    return [item for item in hits if item > cutoff]


def tenant_scope(owner_id: str) -> str:
    """Primary key for a tenant's rate and byte row."""
    return f"t:{owner_id}"


def session_scope(session_id: uuid.UUID) -> str:
    """Primary key for a session byte row."""
    return f"s:{session_id}"


def accepted_hits(hits: list[float], now: float, limit: int) -> list[float]:
    """Append ``now`` or raise when the window is already full."""
    if len(hits) >= limit:
        raise QuotaExceededError("rate limit exceeded")
    hits.append(now)
    return hits


def next_bytes(used: int, nbytes: int, cap: int, message: str) -> int:
    """Return the new total or raise when it would pass ``cap``."""
    updated = used + nbytes
    if updated > cap:
        raise QuotaExceededError(message)
    return updated


def released_bytes(used: int, nbytes: int) -> int:
    """Subtract ``nbytes``, flooring at zero."""
    leftover = used - nbytes
    if leftover > 0:
        return leftover
    return 0
