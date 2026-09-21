"""Async REST client for pixeldive ``/api/v1``."""

from __future__ import annotations

from typing import Self

import httpx

from pixeldive_sdk.rest_images import RestImageMixin
from pixeldive_sdk.rest_sessions import RestSessionMixin
from pixeldive_sdk.rest_upload import RestPathUploadMixin


class RestClient(RestSessionMixin, RestImageMixin, RestPathUploadMixin):
    """Thin httpx wrapper around the session REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
        owns_client: bool | None = None,
        verify: bool | str = True,
        cert: str | tuple[str, str] | tuple[str, str, str] | None = None,
    ) -> None:
        """Bind a base URL, optional bearer token, and optional TLS verify/cert."""
        self._base = base_url.rstrip("/")
        self._token = token
        self._owns_client = client is None if owns_client is None else owns_client
        self._http = client or httpx.AsyncClient(
            base_url=self._base,
            timeout=timeout,
            verify=verify,
            cert=cert,
        )

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
