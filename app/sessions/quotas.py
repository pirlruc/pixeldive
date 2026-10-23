"""Per-tenant request and upload-byte quotas (SEC-002, SEC-004, SEC-005)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable

from app.exceptions import QuotaExceededError, QuotaUnavailableError
from app.sessions.auth import Principal
from app.sessions.quota_limits import QuotaLimits
from app.sessions.quota_memory import MemoryQuotaStore
from app.sessions.quota_redis import RedisQuotaStore
from app.sessions.quota_sql import SqlQuotaStore

_BACKENDS = frozenset({"memory", "postgres", "redis"})
_Store = MemoryQuotaStore | SqlQuotaStore | RedisQuotaStore


def resolve_quota_backend(backend: str, database_url: str, redis_url: str) -> str:
    """Pick memory, postgres, or redis from an explicit name or URLs."""
    choice = backend.strip().lower()
    if choice in _BACKENDS:
        return choice
    if choice:
        msg = "quota_backend must be memory, postgres, or redis"
        raise ValueError(msg)
    if redis_url.strip():
        return "redis"
    if database_url.startswith("postgresql"):
        return "postgres"
    return "memory"


def build_store(backend: str, database_url: str, redis_url: str) -> _Store:
    """Construct the store for an already resolved backend name."""
    if backend == "postgres":
        return SqlQuotaStore(database_url)
    if backend == "redis":
        return RedisQuotaStore(redis_url)
    return MemoryQuotaStore()


class TenantQuota:
    """Rate and byte caps. ``principal is None`` stays unlimited.

    The default store is an in-process ``asyncio.Lock`` counter. PostgreSQL and
    Redis are selected by ``quota_from_settings`` when a shared URL is set.
    """

    def __init__(
        self,
        requests_per_window: int,
        window_seconds: float,
        tenant_max_bytes: int,
        session_max_bytes: int,
        *,
        backend: str = "",
        database_url: str = "",
        redis_url: str = "",
        store: _Store | None = None,
    ) -> None:
        """Bind caps and a store. Tests that omit URLs stay in-process."""
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.tenant_max_bytes = tenant_max_bytes
        self.session_max_bytes = session_max_bytes
        self._limits = QuotaLimits(
            requests_per_window,
            window_seconds,
            tenant_max_bytes,
            session_max_bytes,
        )
        if store is None:
            self.backend = resolve_quota_backend(backend, database_url, redis_url)
            self._store: _Store = build_store(self.backend, database_url, redis_url)
            return
        self.backend = backend or "memory"
        self._store = store

    async def hit(self, principal: Principal | None) -> None:
        """Count one request; raise when the window is full."""
        if principal is None or self.requests_per_window <= 0:
            return
        await self._run(self._store.hit(principal.owner_id, self._limits))

    async def reserve_bytes(
        self,
        principal: Principal | None,
        session_id: uuid.UUID,
        nbytes: int,
    ) -> None:
        """Reserve upload bytes against tenant and session caps."""
        owner_id = _byte_owner(principal, nbytes, self.tenant_max_bytes, self.session_max_bytes)
        if owner_id is None:
            return
        await self._run(self._store.reserve(owner_id, session_id, nbytes, self._limits))

    async def release_bytes(
        self,
        principal: Principal | None,
        session_id: uuid.UUID,
        nbytes: int,
    ) -> None:
        """Return reserved bytes after a failed persist so retries are not starved."""
        owner_id = _byte_owner(principal, nbytes, self.tenant_max_bytes, self.session_max_bytes)
        if owner_id is None:
            return
        await self._run(self._store.release(owner_id, session_id, nbytes, self._limits))

    async def aclose(self) -> None:
        """Close a shared-store client. Memory has nothing to close."""
        await self._store.aclose()

    async def _run(self, op: Awaitable[None]) -> None:
        """Fail closed when a configured shared store cannot be reached."""
        try:
            await op
        except QuotaExceededError:
            raise
        except Exception as exc:
            raise QuotaUnavailableError("quota store unavailable") from exc


def _byte_owner(
    principal: Principal | None,
    nbytes: int,
    tenant_cap: int,
    session_cap: int,
) -> str | None:
    """Return the tenant id when byte caps apply, else None."""
    if principal is None or nbytes <= 0:
        return None
    if tenant_cap <= 0 and session_cap <= 0:
        return None
    return principal.owner_id


def quota_from_settings(
    requests_per_window: int,
    window_seconds: float,
    tenant_max_bytes: int,
    session_max_bytes: int,
    *,
    backend: str = "",
    database_url: str = "",
    redis_url: str = "",
) -> TenantQuota:
    """Build a TenantQuota from unpacked settings fields."""
    return TenantQuota(
        requests_per_window,
        window_seconds,
        tenant_max_bytes,
        session_max_bytes,
        backend=backend,
        database_url=database_url,
        redis_url=redis_url,
    )
