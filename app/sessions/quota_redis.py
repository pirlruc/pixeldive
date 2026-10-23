"""Optional Redis quota hot path (SEC-005). PostgreSQL remains the default shared store."""

from __future__ import annotations

import uuid
from typing import Protocol, cast

from redis.asyncio import Redis

from app.exceptions import QuotaExceededError
from app.sessions.quota_limits import QuotaLimits

_RATE = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
if n > tonumber(ARGV[2]) then
  redis.call('DECR', KEYS[1])
  return 0
end
return 1
"""

_RESERVE = """
local add = tonumber(ARGV[1])
local tcap = tonumber(ARGV[2])
local scap = tonumber(ARGV[3])
if tcap > 0 then
  local used = tonumber(redis.call('GET', KEYS[1]) or '0')
  if used + add > tcap then
    return 1
  end
end
if scap > 0 then
  local used = tonumber(redis.call('GET', KEYS[2]) or '0')
  if used + add > scap then
    return 2
  end
end
if tcap > 0 then
  redis.call('INCRBY', KEYS[1], add)
end
if scap > 0 then
  redis.call('INCRBY', KEYS[2], add)
end
return 0
"""

_RELEASE = """
local sub = tonumber(ARGV[1])
local tcap = tonumber(ARGV[2])
local scap = tonumber(ARGV[3])
local function give(key, cap)
  if cap <= 0 then
    return
  end
  local used = tonumber(redis.call('GET', key) or '0')
  local left = used - sub
  if left > 0 then
    redis.call('SET', key, left)
  else
    redis.call('DEL', key)
  end
end
give(KEYS[1], tcap)
give(KEYS[2], scap)
return 1
"""

_TENANT_CODE = 1
_SESSION_CODE = 2


class RedisEval(Protocol):
    """Async Redis subset used by the quota store."""

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object:
        """Run a Lua script."""

    async def aclose(self) -> None:
        """Close the client."""


def expire_seconds(window: float) -> int:
    """Ceil a rate window to at least one Redis TTL second."""
    whole = int(window)
    if window > whole:
        whole += 1
    if whole < 1:
        return 1
    return whole


def rate_key(owner_id: str) -> str:
    """Redis key for one tenant's fixed window."""
    return f"pd:rate:{owner_id}"


def tenant_bytes_key(owner_id: str) -> str:
    """Redis key for one tenant's reserved bytes."""
    return f"pd:bytes:t:{owner_id}"


def session_bytes_key(session_id: uuid.UUID) -> str:
    """Redis key for one session's reserved bytes."""
    return f"pd:bytes:s:{session_id}"


def connect_redis(url: str) -> Redis:
    """Open a Redis client. The URL comes from the environment, not from code."""
    return cast(
        Redis,
        Redis.from_url(
            url,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
            decode_responses=True,
        ),
    )


def raise_reserve(code: int) -> None:
    """Map a reserve script status onto a quota error."""
    if code == _TENANT_CODE:
        raise QuotaExceededError("tenant upload quota exceeded")
    if code == _SESSION_CODE:
        raise QuotaExceededError("session upload quota exceeded")


class RedisQuotaStore:
    """INCR/TTL rate limit and byte counters in Redis."""

    def __init__(self, redis_url: str, client: RedisEval | None = None) -> None:
        """Connect lazily unless tests already supplied a client."""
        self._url = redis_url
        self._held = client

    async def aclose(self) -> None:
        """Close the client if this store opened it."""
        if self._held is not None:
            await self._held.aclose()
            self._held = None

    async def hit(self, owner_id: str, limits: QuotaLimits) -> None:
        """Share one fixed-window rate budget across processes."""
        allowed = await self._eval(
            _RATE,
            [rate_key(owner_id)],
            [str(expire_seconds(limits.window_seconds)), str(limits.requests_per_window)],
        )
        if allowed == 0:
            raise QuotaExceededError("rate limit exceeded")

    async def reserve(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Reserve tenant and session bytes in one script."""
        code = await self._eval(
            _RESERVE,
            [tenant_bytes_key(owner_id), session_bytes_key(session_id)],
            [str(nbytes), str(limits.tenant_max_bytes), str(limits.session_max_bytes)],
        )
        raise_reserve(code)

    async def release(
        self,
        owner_id: str,
        session_id: uuid.UUID,
        nbytes: int,
        limits: QuotaLimits,
    ) -> None:
        """Return reserved bytes for the caps that are enabled."""
        await self._eval(
            _RELEASE,
            [tenant_bytes_key(owner_id), session_bytes_key(session_id)],
            [str(nbytes), str(limits.tenant_max_bytes), str(limits.session_max_bytes)],
        )

    async def _eval(self, script: str, keys: list[str], args: list[str]) -> int:
        """Run ``script`` and return its integer status."""
        client = self._client()
        result = await _await_eval(client, script, keys, args)
        return int(cast(str, result))

    def _client(self) -> RedisEval:
        """Return the injected client or open one from the URL."""
        if self._held is not None:
            return self._held
        if not self._url.strip():
            msg = "quota redis url is empty"
            raise RuntimeError(msg)
        self._held = connect_redis(self._url)
        return self._held


async def _await_eval(client: RedisEval, script: str, keys: list[str], args: list[str]) -> object:
    """Await Redis eval. redis-py types the result as awaitable or plain."""
    result = client.eval(script, len(keys), *keys, *args)
    if hasattr(result, "__await__"):
        return await result
    return result
