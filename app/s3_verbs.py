"""Object get/put/head/list methods mixed into ``AioS3Adapter``."""

from __future__ import annotations

from typing import Any, cast

from app.s3_invoke import invoke


class S3ObjectMixin:
    """aiobotocore object verbs used by ``S3CompatibleStorage``."""

    async def _ensure(self) -> Any:
        """Return the open client; implemented by AioS3Adapter."""
        raise NotImplementedError  # pragma: no cover

    async def put_object(self, **kwargs: object) -> object:
        """Upload an object."""
        return await invoke(self._ensure, "put_object", **kwargs)

    async def get_object(self, **kwargs: object) -> dict[str, Any]:
        """Download an object."""
        return cast(dict[str, Any], await invoke(self._ensure, "get_object", **kwargs))

    async def delete_object(self, **kwargs: object) -> object:
        """Delete an object."""
        return await invoke(self._ensure, "delete_object", **kwargs)

    async def head_object(self, **kwargs: object) -> object:
        """Probe object existence."""
        return await invoke(self._ensure, "head_object", **kwargs)

    async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """List object keys in the bucket."""
        return cast(dict[str, object], await invoke(self._ensure, "list_objects_v2", **kwargs))
