"""In-process async quota counters for tests and single-process dev."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque

from app.exceptions import QuotaExceededError
from app.sessions.quota_limits import QuotaLimits


class MemoryQuotaStore:
    """Sliding window and byte caps guarded by ``asyncio.Lock``."""

    def __init__(self) -> None:
        """Start with empty counters."""
        self._hits: dict[str, deque[float]] = {}
        self._tenant_bytes: dict[str, int] = {}
        self._session_bytes: dict[uuid.UUID, int] = {}
        self._lock = asyncio.Lock()

    async def hit(self, owner_id: str, limits: QuotaLimits) -> None:
        """Count one request; raise when the sliding window is full."""
        async with self._lock:
            _record_hit(self._hits, owner_id, limits)

    async def reserve(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Reserve upload bytes against tenant and session caps."""
        async with self._lock:
            _reject_if_over(
                self._tenant_bytes.get(owner_id, 0),
                nbytes,
                limits.tenant_max_bytes,
                "tenant upload quota exceeded",
            )
            _reject_if_over(
                self._session_bytes.get(session_id, 0),
                nbytes,
                limits.session_max_bytes,
                "session upload quota exceeded",
            )
            _add_bytes(self._tenant_bytes, owner_id, nbytes, limits.tenant_max_bytes)
            _add_bytes(self._session_bytes, session_id, nbytes, limits.session_max_bytes)

    async def release(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Return reserved bytes after a failed persist."""
        async with self._lock:
            _sub_bytes(self._tenant_bytes, owner_id, nbytes, limits.tenant_max_bytes)
            _sub_bytes(self._session_bytes, session_id, nbytes, limits.session_max_bytes)

    async def aclose(self) -> None:
        """No connections to close."""


def monotonic_now() -> float:
    """Clock for the in-process sliding window."""
    return time.monotonic()


def _record_hit(hits: dict[str, deque[float]], owner_id: str, limits: QuotaLimits) -> None:
    """Append one timestamp after dropping hits outside the window."""
    now = monotonic_now()
    bucket = hits.setdefault(owner_id, deque())
    cutoff = now - limits.window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= limits.requests_per_window:
        raise QuotaExceededError("rate limit exceeded")
    bucket.append(now)


def _reject_if_over(used: int, nbytes: int, cap: int, message: str) -> None:
    """Raise when ``used + nbytes`` would exceed ``cap``."""
    if cap > 0 and used + nbytes > cap:
        raise QuotaExceededError(message)


def _add_bytes[K](store: dict[K, int], key: K, nbytes: int, cap: int) -> None:
    """Increment ``store[key]`` when the matching cap is enabled."""
    if cap > 0:
        store[key] = store.get(key, 0) + nbytes


def _sub_bytes[K](store: dict[K, int], key: K, nbytes: int, cap: int) -> None:
    """Decrement ``store[key]``, dropping the entry at zero."""
    if cap <= 0:
        return
    leftover = store.get(key, 0) - nbytes
    if leftover > 0:
        store[key] = leftover
        return
    store.pop(key, None)
