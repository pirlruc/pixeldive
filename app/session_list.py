"""Paginated session and image listing mixed into SessionService."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlmodel import col

from app.auth import Principal
from app.models import Session, SessionImage
from app.pagination import Page, clamp_limit, cursor_predicate, next_cursor
from app.session_host import SessionHost


class SessionListMixin(SessionHost):
    """Cursor-paged list helpers used by SessionService."""

    async def list_sessions(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        principal: Principal | None = None,
    ) -> Page[Session]:
        """Return a page of sessions newest-first, scoped to the caller."""
        self._quota.hit(principal)
        page_size = clamp_limit(
            limit,
            self._settings.list_default_limit,
            self._settings.list_max_limit,
        )
        statement = select(Session).order_by(
            col(Session.created_at).desc(),
            col(Session.id).desc(),
        )
        if principal is not None:
            statement = statement.where(col(Session.owner_id) == principal.owner_id)
        predicate = cursor_predicate(
            col(Session.created_at),
            col(Session.id),
            cursor,
            descending=True,
        )
        if predicate is not None:
            statement = statement.where(predicate)
        statement = statement.limit(page_size + 1)
        async with self._factory() as db:
            result = await db.execute(statement)
            rows = list(result.scalars().all())
        items, next_page = next_cursor(
            rows, page_size, lambda row: row.created_at, lambda row: row.id
        )
        return Page(items=items, next_cursor=next_page)

    async def list_images(
        self,
        session_id: uuid.UUID,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        principal: Principal | None = None,
    ) -> Page[SessionImage]:
        """Return a page of image metadata for a session."""
        self._quota.hit(principal)
        page_size = clamp_limit(
            limit,
            self._settings.list_default_limit,
            self._settings.list_max_limit,
        )
        async with self._factory() as db:
            await self._require_session(db, session_id, principal)
            statement = (
                select(SessionImage)
                .where(SessionImage.session_id == session_id)  # type: ignore[arg-type]
                .order_by(col(SessionImage.uploaded_at), col(SessionImage.id))
            )
            predicate = cursor_predicate(
                col(SessionImage.uploaded_at),
                col(SessionImage.id),
                cursor,
                descending=False,
            )
            if predicate is not None:
                statement = statement.where(predicate)
            statement = statement.limit(page_size + 1)
            result = await db.execute(statement)
            rows = list(result.scalars().all())
        items, next_page = next_cursor(
            rows,
            page_size,
            lambda row: row.uploaded_at,
            lambda row: row.id,
        )
        return Page(items=items, next_cursor=next_page)
