"""Row-locked SQL updates for shared quota counters."""

from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.sessions.quota_limits import QuotaLimits
from app.sessions.quota_sql_rows import (
    QuotaRow,
    accepted_hits,
    dialect_name,
    lock_select,
    next_bytes,
    parse_hits,
    prune_hits,
    released_bytes,
    session_scope,
    tenant_scope,
)

_INSERT = (
    "INSERT INTO tenant_quota (scope, bytes_used, hits) "
    "VALUES (:scope, 0, '[]') ON CONFLICT (scope) DO NOTHING"
)
_UPDATE_BYTES = "UPDATE tenant_quota SET bytes_used = :used WHERE scope = :scope"
_UPDATE_HITS = "UPDATE tenant_quota SET hits = :hits WHERE scope = :scope"


def wall_now() -> float:
    """Wall clock shared by every replica's rate window."""
    return time.time()


async def record_hit(
    conn: AsyncConnection,
    scope: str,
    limits: QuotaLimits,
    database_url: str,
) -> None:
    """Insert one timestamp or raise when the window is full."""
    row = await locked_row(conn, scope, database_url)
    now = wall_now()
    hits = prune_hits(parse_hits(row.hits), now, limits.window_seconds)
    accepted = accepted_hits(hits, now, limits.requests_per_window)
    await conn.execute(text(_UPDATE_HITS), {"scope": scope, "hits": json.dumps(accepted)})


async def reserve_both(
    conn: AsyncConnection,
    owner_id: str,
    session_id: uuid.UUID,
    nbytes: int,
    limits: QuotaLimits,
    database_url: str,
) -> None:
    """Apply tenant then session caps so lock order stays stable."""
    if limits.tenant_max_bytes > 0:
        await _add_capped(
            conn,
            tenant_scope(owner_id),
            nbytes,
            limits.tenant_max_bytes,
            "tenant upload quota exceeded",
            database_url,
        )
    if limits.session_max_bytes > 0:
        await _add_capped(
            conn,
            session_scope(session_id),
            nbytes,
            limits.session_max_bytes,
            "session upload quota exceeded",
            database_url,
        )


async def release_both(
    conn: AsyncConnection,
    owner_id: str,
    session_id: uuid.UUID,
    nbytes: int,
    limits: QuotaLimits,
    database_url: str,
) -> None:
    """Give bytes back to each enabled cap."""
    if limits.tenant_max_bytes > 0:
        await _give_back(conn, tenant_scope(owner_id), nbytes, database_url)
    if limits.session_max_bytes > 0:
        await _give_back(conn, session_scope(session_id), nbytes, database_url)


async def _add_capped(
    conn: AsyncConnection,
    scope: str,
    nbytes: int,
    cap: int,
    message: str,
    database_url: str,
) -> None:
    """Lock ``scope`` and add ``nbytes`` when the cap allows it."""
    row = await locked_row(conn, scope, database_url)
    await conn.execute(
        text(_UPDATE_BYTES),
        {"scope": scope, "used": next_bytes(row.bytes_used, nbytes, cap, message)},
    )


async def _give_back(conn: AsyncConnection, scope: str, nbytes: int, database_url: str) -> None:
    """Subtract ``nbytes``, flooring at zero."""
    row = await locked_row(conn, scope, database_url)
    await conn.execute(
        text(_UPDATE_BYTES),
        {"scope": scope, "used": released_bytes(row.bytes_used, nbytes)},
    )


async def locked_row(conn: AsyncConnection, scope: str, database_url: str) -> QuotaRow:
    """Insert the scope if needed, then read it under the dialect lock."""
    await conn.execute(text(_INSERT), {"scope": scope})
    statement = text(lock_select(dialect_name(database_url)))
    result = await conn.execute(statement, {"scope": scope})
    row = result.one()
    return QuotaRow(int(row.bytes_used), str(row.hits))
