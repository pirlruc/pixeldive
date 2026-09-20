"""In-process per-tenant request and upload-byte quotas (SEC-002)."""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from app.auth import Principal
from app.exceptions import QuotaExceededError


@dataclass
class TenantQuota:
    """Sliding-window request limiter plus cumulative byte caps.

    Limits of ``0`` mean unlimited. ``principal is None`` (AUTH_REQUIRED=false)
    skips enforcement so local/dev stays unbounded.
    """

    requests_per_window: int
    window_seconds: float
    tenant_max_bytes: int
    session_max_bytes: int
    _hits: dict[str, deque[float]] = field(default_factory=dict)
    _tenant_bytes: dict[str, int] = field(default_factory=dict)
    _session_bytes: dict[uuid.UUID, int] = field(default_factory=dict)

    def hit(self, principal: Principal | None) -> None:
        """Count one request; raise when the sliding window is full."""
        if principal is None or self.requests_per_window <= 0:
            return
        now = time.monotonic()
        bucket = self._hits.setdefault(principal.owner_id, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.requests_per_window:
            raise QuotaExceededError("rate limit exceeded")
        bucket.append(now)

    def reserve_bytes(
        self,
        principal: Principal | None,
        session_id: uuid.UUID,
        nbytes: int,
    ) -> None:
        """Reserve upload bytes against tenant and session caps."""
        if principal is None or nbytes <= 0:
            return
        owner = principal.owner_id
        _reject_if_over(
            self._tenant_bytes.get(owner, 0),
            nbytes,
            self.tenant_max_bytes,
            "tenant upload quota exceeded",
        )
        _reject_if_over(
            self._session_bytes.get(session_id, 0),
            nbytes,
            self.session_max_bytes,
            "session upload quota exceeded",
        )
        _add_bytes(self._tenant_bytes, owner, nbytes, self.tenant_max_bytes)
        _add_bytes(self._session_bytes, session_id, nbytes, self.session_max_bytes)

    def release_bytes(
        self,
        principal: Principal | None,
        session_id: uuid.UUID,
        nbytes: int,
    ) -> None:
        """Return reserved bytes after a failed persist so retries are not starved."""
        if principal is None or nbytes <= 0:
            return
        _sub_bytes(self._tenant_bytes, principal.owner_id, nbytes, self.tenant_max_bytes)
        _sub_bytes(self._session_bytes, session_id, nbytes, self.session_max_bytes)


def _reject_if_over(used: int, nbytes: int, cap: int, message: str) -> None:
    """Raise QuotaExceededError when ``used + nbytes`` would exceed ``cap``."""
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


def quota_from_settings(
    requests_per_window: int,
    window_seconds: float,
    tenant_max_bytes: int,
    session_max_bytes: int,
) -> TenantQuota:
    """Build a TenantQuota from unpacked settings fields."""
    return TenantQuota(
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
        tenant_max_bytes=tenant_max_bytes,
        session_max_bytes=session_max_bytes,
    )
