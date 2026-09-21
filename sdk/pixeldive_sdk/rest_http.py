"""Shared httpx helpers for RestClient mixins."""

from __future__ import annotations

from typing import Any

import httpx


class RestHttpMixin:
    """JSON request helper and optional per-request bearer header."""

    _http: httpx.AsyncClient
    _token: str | None

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization when this client was constructed with a token."""
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def _page_params(self, limit: int, cursor: str | None) -> dict[str, Any]:
        """Build list query parameters."""
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return params

    def _form_fields(self, metadata: str | None) -> dict[str, str]:
        """Optional multipart metadata field used by image uploads."""
        if metadata is None:
            return {}
        return {"metadata": metadata}

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue an HTTP request, merging bearer auth onto a shared client."""
        headers = dict(kwargs.pop("headers", None) or {})
        headers.update(self._auth_headers())
        response = await self._http.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        """Issue a request and decode JSON (``None`` when the body is empty)."""
        response = await self._request(method, path, **kwargs)
        if not response.content:
            return None
        payload: Any = response.json()
        return payload
