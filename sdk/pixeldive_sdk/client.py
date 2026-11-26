"""Async REST client for pixeldive ``/api/v1``."""

from __future__ import annotations

import ssl
from typing import Self

import httpx

from pixeldive_sdk.rest_images import RestImageMixin
from pixeldive_sdk.rest_sessions import RestSessionMixin
from pixeldive_sdk.rest_upload import RestPathUploadMixin


def _reject_cleartext_token(base: str, token: str | None, allow_local_http: bool) -> None:
    """A bearer token stays off cleartext except explicit loopback."""
    if not token or not base.startswith("http://"):
        return
    host = base.split("/", 3)[2].rsplit("@", 1)[-1].split(":", 1)[0].strip("[]")
    if allow_local_http and host in {"localhost", "127.0.0.1", "::1"}:
        return
    raise ValueError("a token requires TLS unless allow_local_http is set for loopback")


def as_ssl_verify(verify: bool | str | ssl.SSLContext) -> bool | ssl.SSLContext:
    """Accept a CA path string; httpx wants bool or SSLContext."""
    if isinstance(verify, str):
        return ssl.create_default_context(cafile=verify)
    return verify


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
        verify: bool | str | ssl.SSLContext = True,
        cert: str | tuple[str, str] | tuple[str, str, str] | None = None,
        allow_local_http: bool = False,
    ) -> None:
        """Bind a base URL, optional bearer token, and optional TLS verify/cert."""
        self._base = base_url.rstrip("/")
        _reject_cleartext_token(self._base, token, allow_local_http)
        if verify is False:
            raise ValueError("verify=False is refused; pass a CA or an SSLContext")
        self._token = token
        self._owns_client = client is None if owns_client is None else owns_client
        self._http = client or httpx.AsyncClient(
            base_url=self._base,
            timeout=timeout,
            verify=as_ssl_verify(verify),
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
