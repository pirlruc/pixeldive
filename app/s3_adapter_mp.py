"""Multipart methods mixed into ``AioS3Adapter`` (PERF-003)."""

from __future__ import annotations

from typing import Any, cast

from app.s3_invoke import invoke


class S3MultipartMixin:
    """aiobotocore multipart verbs used by ``put_file_multipart``."""

    async def _ensure(self) -> Any:
        """Return the open client; implemented by AioS3Adapter."""
        raise NotImplementedError  # pragma: no cover

    async def create_multipart_upload(self, **kwargs: object) -> dict[str, object]:
        """Start a multipart upload."""
        return cast(
            dict[str, object],
            await invoke(self._ensure, "create_multipart_upload", **kwargs),
        )

    async def upload_part(self, **kwargs: object) -> dict[str, object]:
        """Upload one part."""
        return cast(dict[str, object], await invoke(self._ensure, "upload_part", **kwargs))

    async def complete_multipart_upload(self, **kwargs: object) -> object:
        """Finish a multipart upload."""
        return await invoke(self._ensure, "complete_multipart_upload", **kwargs)

    async def abort_multipart_upload(self, **kwargs: object) -> object:
        """Abort a multipart upload."""
        return await invoke(self._ensure, "abort_multipart_upload", **kwargs)
