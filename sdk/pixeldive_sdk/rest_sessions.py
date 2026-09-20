"""Session CRUD methods for ``RestClient``."""

from __future__ import annotations

from typing import Any

from pixeldive_sdk.ids import resource_id
from pixeldive_sdk.rest_http import RestHttpMixin


class RestSessionMixin(RestHttpMixin):
    """Health, ready, and session CRUD against ``/api/v1``."""

    async def health(self) -> dict[str, Any]:
        """GET /health."""
        payload: dict[str, Any] = await self._json("GET", "/health")
        return payload

    async def ready(self) -> dict[str, Any]:
        """GET /ready."""
        payload: dict[str, Any] = await self._json("GET", "/ready")
        return payload

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/sessions."""
        data: dict[str, Any] = await self._json("POST", "/api/v1/sessions", json=payload)
        return data

    async def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/sessions."""
        payload: dict[str, Any] = await self._json(
            "GET",
            "/api/v1/sessions",
            params=self._page_params(limit, cursor),
        )
        return payload

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """GET /api/v1/sessions/{id}."""
        payload: dict[str, Any] = await self._json(
            "GET",
            f"/api/v1/sessions/{resource_id(session_id)}",
        )
        return payload

    async def update_session(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        merge_metadata: bool = False,
    ) -> dict[str, Any]:
        """PUT /api/v1/sessions/{id}."""
        body = dict(payload)
        body["merge_metadata"] = merge_metadata
        data: dict[str, Any] = await self._json(
            "PUT",
            f"/api/v1/sessions/{resource_id(session_id)}",
            json=body,
        )
        return data

    async def delete_session(self, session_id: str) -> None:
        """DELETE /api/v1/sessions/{id}."""
        await self._request("DELETE", f"/api/v1/sessions/{resource_id(session_id)}")
