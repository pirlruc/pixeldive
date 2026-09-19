"""Async REST client for pixeldive ``/api/v1``."""

from __future__ import annotations

from typing import Self

import httpx

from pixeldive_sdk.rest_images import RestImageMixin
from pixeldive_sdk.rest_sessions import RestSessionMixin


class RestClient(RestSessionMixin, RestImageMixin):
    """Thin httpx wrapper around the session REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Bind a base URL, optional bearer token, and optional shared client."""
        self._base = base_url.rstrip("/")
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._owns_client = client is None
        self._http = client or httpx.AsyncClient(
            base_url=self._base,
            headers=headers,
            timeout=timeout,
        )
        if client is not None and token:
            self._http.headers["Authorization"] = f"Bearer {token}"

    async def __aenter__(self) -> Self:
        """Return self for ``async with``."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close an owned httpx client."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying client when this wrapper created it."""
        if self._owns_client:
            await self._http.aclose()
