"""Lazy aiobotocore S3 client used by ``S3CompatibleStorage``."""

from __future__ import annotations

import asyncio
from typing import Any

from app.blobs.s3_session import s3_client_context
from app.blobs.s3_types import S3ObjectClient
from app.blobs.s3_verbs import S3VerbMixin
from app.config import Settings


class AioS3Adapter(S3VerbMixin):
    """Create an aiobotocore client on first use so ``build_storage`` stays sync."""

    def __init__(self, settings: Settings) -> None:
        """Bind settings; the HTTP client is opened lazily."""
        self._settings = settings
        self._lock = asyncio.Lock()
        self._client: Any | None = None
        self._cm: Any | None = None

    async def _ensure(self) -> Any:
        """Return the open client, creating it once."""
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            self._cm = s3_client_context(self._settings)
            self._client = await self._cm.__aenter__()
            return self._client

    async def aclose(self) -> None:
        """Exit the client context if it was opened."""
        cm, self._cm, self._client = self._cm, None, None
        if cm is not None:
            await cm.__aexit__(None, None, None)


def default_s3_client(settings: Settings) -> S3ObjectClient:
    """Return a lazy async adapter; local-only deploys never import aiobotocore."""
    return AioS3Adapter(settings)
