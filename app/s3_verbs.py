"""Object and multipart methods mixed into ``AioS3Adapter``."""

from __future__ import annotations

from typing import Any, cast

from app.s3_invoke import invoke


class S3VerbMixin:
    """aiobotocore verbs used by ``S3CompatibleStorage`` and multipart PUT."""

    async def _ensure(self) -> Any:
        """Return the open client; implemented by AioS3Adapter."""
        raise NotImplementedError  # pragma: no cover

    async def _call(self, method: str, **kwargs: object) -> Any:
        """Dispatch ``method`` on the lazily opened client."""
        return await invoke(self._ensure, method, **kwargs)

    async def put_object(self, **kwargs: object) -> object:
        """Upload an object."""
        return await self._call("put_object", **kwargs)

    async def get_object(self, **kwargs: object) -> dict[str, Any]:
        """Download an object."""
        return cast(dict[str, Any], await self._call("get_object", **kwargs))

    async def delete_object(self, **kwargs: object) -> object:
        """Delete an object."""
        return await self._call("delete_object", **kwargs)

    async def head_object(self, **kwargs: object) -> object:
        """Probe object existence."""
        return await self._call("head_object", **kwargs)

    async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """List object keys in the bucket."""
        return cast(dict[str, object], await self._call("list_objects_v2", **kwargs))

    async def create_multipart_upload(self, **kwargs: object) -> dict[str, object]:
        """Start a multipart upload."""
        return cast(dict[str, object], await self._call("create_multipart_upload", **kwargs))

    async def upload_part(self, **kwargs: object) -> dict[str, object]:
        """Upload one part."""
        return cast(dict[str, object], await self._call("upload_part", **kwargs))

    async def complete_multipart_upload(self, **kwargs: object) -> object:
        """Finish a multipart upload."""
        return await self._call("complete_multipart_upload", **kwargs)

    async def abort_multipart_upload(self, **kwargs: object) -> object:
        """Abort a multipart upload."""
        return await self._call("abort_multipart_upload", **kwargs)
