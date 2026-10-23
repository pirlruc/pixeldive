"""Shared quota backends (SEC-004 PostgreSQL, SEC-005 Redis)."""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from pathlib import Path

import pytest
from alembic import command
from pydantic import ValidationError
from sqlalchemy import inspect

from app.config import Settings
from app.database import create_engine
from app.error_map import grpc_status, http_status
from app.exceptions import QuotaExceededError, QuotaUnavailableError
from app.migrate import alembic_config, check_sync, upgrade_head
from app.sessions.auth import Principal
from app.sessions.quota_redis import RedisQuotaStore, expire_seconds
from app.sessions.quota_sql import open_engine
from app.sessions.quota_sql_rows import dialect_name, lock_select, parse_hits
from app.sessions.quotas import TenantQuota, quota_from_settings, resolve_quota_backend


def test_backend_selection_prefers_explicit_name() -> None:
    """Memory is the default; a Redis URL beats PostgreSQL; explicit wins."""
    assert resolve_quota_backend("", "sqlite+aiosqlite:///x.db", "") == "memory"
    assert resolve_quota_backend("", "postgresql+asyncpg://db/pixeldive", "") == "postgres"
    assert (
        resolve_quota_backend("", "postgresql+asyncpg://db/pixeldive", "redis://localhost")
        == "redis"
    )
    assert (
        resolve_quota_backend("memory", "postgresql+asyncpg://db/x", "redis://localhost")
        == "memory"
    )
    with pytest.raises(ValueError, match="quota_backend"):
        resolve_quota_backend("disk", "", "")


def test_settings_reject_unknown_quota_backend() -> None:
    """QUOTA_BACKEND only accepts the three store names."""
    with pytest.raises(ValidationError):
        Settings(quota_backend="disk")
    quota = quota_from_settings(0, 60.0, 0, 0, database_url="sqlite+aiosqlite:///t.db")
    assert quota.backend == "memory"


def test_lock_select_and_ttl_helpers() -> None:
    """PostgreSQL locks the row; other dialects and TTLs stay portable."""
    assert "FOR UPDATE" in lock_select(dialect_name("postgresql+asyncpg://db/x"))
    assert "FOR UPDATE" not in lock_select(dialect_name("sqlite+aiosqlite:///x.db"))
    assert expire_seconds(60) == 60
    assert expire_seconds(1.2) == 2
    assert expire_seconds(0) == 1
    with pytest.raises(ValueError, match="list"):
        parse_hits("{}")


def test_memory_quota_lock_is_asyncio() -> None:
    """The in-process counter does not use threading.Lock."""
    import asyncio

    quota = TenantQuota(1, 60.0, 0, 0)
    lock = quota._store._lock  # type: ignore[attr-defined]
    assert isinstance(lock, asyncio.Lock)


def test_quota_unavailable_maps_to_503() -> None:
    """A down shared store is unavailable, not a rate-limit response."""
    exc = QuotaUnavailableError("quota store unavailable")
    assert http_status(exc) == 503
    assert grpc_status(exc).name == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_postgres_engine_opens_without_connecting() -> None:
    """The PostgreSQL branch of the engine helper does not need a live server."""
    engine = open_engine("postgresql+asyncpg://127.0.0.1:1/pixeldive")
    await engine.dispose()


@pytest.mark.asyncio
async def test_anonymous_and_unlimited_skip_a_down_store() -> None:
    """AUTH_REQUIRED=false and zero caps stay unlimited when the store is down."""
    dead = "postgresql+asyncpg://127.0.0.1:1/pixeldive"
    quota = TenantQuota(1, 60.0, 10, 10, backend="postgres", database_url=dead)
    await quota.hit(None)
    await quota.reserve_bytes(None, uuid.uuid4(), 5)
    unlimited = TenantQuota(0, 60.0, 0, 0, backend="redis", redis_url="redis://127.0.0.1:1/0")
    await unlimited.hit(Principal(owner_id="tenant-a"))
    await quota.aclose()
    await unlimited.aclose()


@pytest.mark.asyncio
async def test_shared_store_down_fails_closed() -> None:
    """Configured quotas fail closed when PostgreSQL or Redis cannot be reached."""
    principal = Principal(owner_id="tenant-a")
    postgres = TenantQuota(
        1,
        60.0,
        0,
        0,
        backend="postgres",
        database_url="postgresql+asyncpg://127.0.0.1:1/pixeldive",
    )
    redis = TenantQuota(1, 60.0, 1, 1, backend="redis", redis_url="redis://127.0.0.1:1/0")
    try:
        with pytest.raises(QuotaUnavailableError, match="unavailable"):
            await postgres.hit(principal)
        with pytest.raises(QuotaUnavailableError, match="unavailable"):
            await redis.hit(principal)
        with pytest.raises(QuotaUnavailableError, match="unavailable"):
            await redis.reserve_bytes(principal, uuid.uuid4(), 1)
        blank_redis = TenantQuota(1, 60.0, 0, 0, backend="redis", redis_url="")
        blank_sql = TenantQuota(1, 60.0, 0, 0, backend="postgres", database_url=" ")
        with pytest.raises(QuotaUnavailableError, match="unavailable"):
            await blank_redis.hit(principal)
        with pytest.raises(QuotaUnavailableError, match="unavailable"):
            await blank_sql.hit(principal)
        await blank_redis.aclose()
        await blank_sql.aclose()
    finally:
        await postgres.aclose()
        await redis.aclose()


@pytest.mark.asyncio
async def test_two_sql_quotas_share_one_budget(tmp_path: Path) -> None:
    """Two stores on one SQL URL share rate and byte counters."""
    await _assert_shared_sql(f"sqlite+aiosqlite:///{tmp_path / 'quota.db'}")


@pytest.mark.asyncio
async def test_sql_rate_window_drops_old_hits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hits older than the window do not consume the shared rate budget."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'expire.db'}"
    await upgrade_head(url)
    times = iter([0.0, 5.0])
    monkeypatch.setattr("app.sessions.quota_sql_ops.wall_now", lambda: next(times))
    quota = TenantQuota(1, 1.0, 0, 0, backend="postgres", database_url=url)
    principal = Principal(owner_id=f"expire-{uuid.uuid4()}")
    await quota.hit(principal)
    await quota.hit(principal)
    await quota.aclose()


@pytest.mark.quota_postgres
@pytest.mark.asyncio
async def test_two_postgres_quotas_share_one_budget() -> None:
    """Two processes pointed at one PostgreSQL URL share one budget (SEC-004)."""
    url = os.environ.get("PIXELDIVE_TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("PIXELDIVE_TEST_DATABASE_URL is not a postgresql URL")
    await _assert_shared_sql(url)
    await _assert_concurrent_rate(url)


@pytest.mark.asyncio
async def test_quota_table_is_added_only_by_0002(tmp_path: Path) -> None:
    """0001 leaves tenant_quota absent; 0002 creates it and matches metadata."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'fresh.db'}"
    await asyncio.to_thread(command.upgrade, alembic_config(url), "0001_phase2")
    assert "tenant_quota" not in await _tables(url)
    await upgrade_head(url)
    assert "tenant_quota" in await _tables(url)
    await asyncio.to_thread(check_sync, url)


@pytest.mark.asyncio
async def test_existing_quota_table_survives_upgrade(tmp_path: Path) -> None:
    """create_all leftovers are not created again by 0002."""
    from sqlmodel import SQLModel

    url = f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}"
    await asyncio.to_thread(command.upgrade, alembic_config(url), "0001_phase2")
    engine = create_engine(Settings(database_url=url, auto_create_tables=False, log_json=False))
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    await engine.dispose()
    assert "tenant_quota" in await _tables(url)
    await upgrade_head(url)
    await asyncio.to_thread(check_sync, url)


@pytest.mark.asyncio
async def test_redis_client_maps_rate_and_bytes() -> None:
    """The Redis store honours script statuses without a live server."""
    fake = _FakeRedis()
    store = RedisQuotaStore("redis://unused", client=fake)
    quota = TenantQuota(1, 60.0, 10, 5, backend="redis", store=store)
    principal = Principal(owner_id="tenant-a")
    session_id = uuid.uuid4()
    await quota.hit(principal)
    with pytest.raises(QuotaExceededError, match="rate limit"):
        await quota.hit(principal)
    await quota.reserve_bytes(principal, session_id, 4)
    with pytest.raises(QuotaExceededError, match="session"):
        await quota.reserve_bytes(principal, session_id, 2)
    await quota.release_bytes(principal, session_id, 4)
    await quota.reserve_bytes(principal, session_id, 4)
    wide = TenantQuota(0, 60.0, 3, 0, backend="redis", store=fake_store(fake))
    with pytest.raises(QuotaExceededError, match="tenant"):
        await wide.reserve_bytes(principal, uuid.uuid4(), 4)
    await quota.aclose()
    assert fake.closed


@pytest.mark.quota_redis
@pytest.mark.asyncio
async def test_two_redis_quotas_share_one_rate_budget() -> None:
    """Two processes sharing Redis honour one rate budget (SEC-005)."""
    url = _redis_url()
    if url is None:
        pytest.skip("REDIS_URL is unset and redis is not reachable")
    principal = Principal(owner_id=f"redis-{uuid.uuid4()}")
    left = TenantQuota(1, 60.0, 0, 0, backend="redis", redis_url=url)
    right = TenantQuota(1, 60.0, 0, 0, backend="redis", redis_url=url)
    try:
        await left.hit(principal)
        with pytest.raises(QuotaExceededError, match="rate limit"):
            await right.hit(principal)
        fresh = Principal(owner_id=f"race-{uuid.uuid4()}")
        raced = await asyncio.gather(left.hit(fresh), right.hit(fresh), return_exceptions=True)
    finally:
        await left.aclose()
        await right.aclose()
    assert sum(item is None for item in raced) == 1
    assert sum(isinstance(item, QuotaExceededError) for item in raced) == 1


async def _assert_shared_sql(url: str) -> None:
    """Rate, session bytes, and release are visible to a second store."""
    await upgrade_head(url)
    principal = Principal(owner_id=f"shared-{uuid.uuid4()}")
    session_id = uuid.uuid4()
    left = TenantQuota(1, 30.0, 20, 10, backend="postgres", database_url=url)
    right = TenantQuota(1, 30.0, 20, 10, backend="postgres", database_url=url)
    tenant_only = TenantQuota(0, 60.0, 5, 0, backend="postgres", database_url=url)
    session_only = TenantQuota(0, 60.0, 0, 5, backend="postgres", database_url=url)
    try:
        await left.hit(principal)
        with pytest.raises(QuotaExceededError, match="rate limit"):
            await right.hit(principal)
        await left.reserve_bytes(principal, session_id, 6)
        with pytest.raises(QuotaExceededError, match="session"):
            await right.reserve_bytes(principal, session_id, 6)
        await left.release_bytes(principal, session_id, 2)
        await right.reserve_bytes(principal, session_id, 4)
        other = Principal(owner_id=f"tenant-{uuid.uuid4()}")
        other_session = uuid.uuid4()
        await tenant_only.reserve_bytes(other, other_session, 5)
        with pytest.raises(QuotaExceededError, match="tenant"):
            await tenant_only.reserve_bytes(other, uuid.uuid4(), 1)
        await tenant_only.release_bytes(other, other_session, 5)
        session_only_id = uuid.uuid4()
        await session_only.reserve_bytes(other, session_only_id, 5)
        await session_only.release_bytes(other, session_only_id, 5)
    finally:
        await left.aclose()
        await right.aclose()
        await tenant_only.aclose()
        await session_only.aclose()


async def _assert_concurrent_rate(url: str) -> None:
    """One of two overlapping hits is rejected when the cap is 1."""
    principal = Principal(owner_id=f"race-{uuid.uuid4()}")
    left = TenantQuota(1, 60.0, 0, 0, backend="postgres", database_url=url)
    right = TenantQuota(1, 60.0, 0, 0, backend="postgres", database_url=url)
    try:
        results = await asyncio.gather(
            left.hit(principal), right.hit(principal), return_exceptions=True
        )
    finally:
        await left.aclose()
        await right.aclose()
    assert sum(item is None for item in results) == 1
    assert sum(isinstance(item, QuotaExceededError) for item in results) == 1


async def _tables(url: str) -> set[str]:
    """List tables for ``url``."""
    engine = create_engine(Settings(database_url=url, auto_create_tables=False, log_json=False))
    async with engine.connect() as connection:
        names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    await engine.dispose()
    return names


def _redis_url() -> str | None:
    """Use REDIS_URL, or localhost:6379 when a Docker Redis answers."""
    configured = os.environ.get("REDIS_URL", "").strip()
    if configured:
        return configured
    if _port_open("127.0.0.1", 6379):
        return "redis://127.0.0.1:6379/0"
    return None


def _port_open(host: str, port: int) -> bool:
    """Return True when a TCP connect succeeds."""
    probe = socket.socket()
    probe.settimeout(0.2)
    try:
        probe.connect((host, port))
    except OSError:
        return False
    else:
        return True
    finally:
        probe.close()


class _FakeRedis:
    """In-memory stand-in for the quota Lua scripts."""

    def __init__(self) -> None:
        self.rate: dict[str, int] = {}
        self.blob: dict[str, int] = {}
        self.closed = False

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> int:
        keys = list(keys_and_args[:numkeys])
        argv = list(keys_and_args[numkeys:])
        if "EXPIRE" in script:
            return self._rate(keys[0], int(argv[1]))
        if "INCRBY" in script:
            return self._reserve(keys, argv)
        self._release(keys, argv)
        return 1

    async def aclose(self) -> None:
        self.closed = True

    def _rate(self, key: str, limit: int) -> int:
        count = self.rate.get(key, 0) + 1
        if count > limit:
            return 0
        self.rate[key] = count
        return 1

    def _reserve(self, keys: list[str], argv: list[str]) -> int:
        add, tenant_cap, session_cap = (int(item) for item in argv)
        if tenant_cap > 0 and self.blob.get(keys[0], 0) + add > tenant_cap:
            return 1
        if session_cap > 0 and self.blob.get(keys[1], 0) + add > session_cap:
            return 2
        self._add(keys[0], add, tenant_cap)
        self._add(keys[1], add, session_cap)
        return 0

    def _release(self, keys: list[str], argv: list[str]) -> None:
        sub, tenant_cap, session_cap = (int(item) for item in argv)
        self._sub(keys[0], sub, tenant_cap)
        self._sub(keys[1], sub, session_cap)

    def _add(self, key: str, amount: int, cap: int) -> None:
        if cap > 0:
            self.blob[key] = self.blob.get(key, 0) + amount

    def _sub(self, key: str, amount: int, cap: int) -> None:
        if cap > 0:
            self.blob[key] = max(0, self.blob.get(key, 0) - amount)


def fake_store(client: _FakeRedis) -> RedisQuotaStore:
    """Build a store around an existing fake so two quotas can share it."""
    return RedisQuotaStore("redis://unused", client=client)
