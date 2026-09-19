"""Session CRUD methods for ``RestClient``."""

from __future__ import annotations

from typing import Any

import httpx


class RestSessionMixin:
    """Health, ready, and session CRUD against ``/api/v1``."""

    _http: httpx.AsyncClient

    async def health(self) -> dict[str, Any]:
        """GET /health."""
        response = await self._http.get("/health")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def ready(self) -> dict[str, Any]:
        """GET /ready."""
        response = await self._http.get("/ready")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/sessions."""
        body = await self._http.post("/api/v1/sessions", json=payload)
        body.raise_for_status()
        data: dict[str, Any] = body.json()
        return data

    async def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/sessions."""
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        response = await self._http.get("/api/v1/sessions", params=params)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """GET /api/v1/sessions/{id}."""
        response = await self._http.get(f"/api/v1/sessions/{session_id}")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
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
        response = await self._http.put(f"/api/v1/sessions/{session_id}", json=body)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def delete_session(self, session_id: str) -> None:
        """DELETE /api/v1/sessions/{id}."""
        response = await self._http.delete(f"/api/v1/sessions/{session_id}")
        response.raise_for_status()
