"""Lazy aiobotocore S3 client used by ``S3CompatibleStorage``."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from app.config import Settings
from app.s3_types import S3ObjectClient


class AioS3Adapter:
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
            self._client = await self._open()
            return self._client

    async def _open(self) -> Any:
        """Enter the aiobotocore client context manager."""
        from aiobotocore.session import get_session

        self._cm = get_session().create_client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url,
            region_name=self._settings.s3_region,
            aws_access_key_id=self._settings.aws_access_key_id,
            aws_secret_access_key=self._settings.aws_secret_access_key,
        )
        return await self._cm.__aenter__()

    async def aclose(self) -> None:
        """Exit the client context if it was opened."""
        cm, self._cm, self._client = self._cm, None, None
        if cm is not None:
            await cm.__aexit__(None, None, None)

    async def put_object(self, **kwargs: object) -> object:
        """Upload an object."""
        client = await self._ensure()
        return cast(object, await client.put_object(**kwargs))

    async def get_object(self, **kwargs: object) -> dict[str, Any]:
        """Download an object."""
        client = await self._ensure()
        return cast(dict[str, Any], await client.get_object(**kwargs))

    async def delete_object(self, **kwargs: object) -> object:
        """Delete an object."""
        client = await self._ensure()
        return cast(object, await client.delete_object(**kwargs))

    async def head_object(self, **kwargs: object) -> object:
        """Probe object existence."""
        client = await self._ensure()
        return cast(object, await client.head_object(**kwargs))

    async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """List object keys in the bucket."""
        client = await self._ensure()
        return cast(dict[str, object], await client.list_objects_v2(**kwargs))


def default_s3_client(settings: Settings) -> S3ObjectClient:
    """Return a lazy async adapter; local-only deploys never import aiobotocore."""
    return AioS3Adapter(settings)
