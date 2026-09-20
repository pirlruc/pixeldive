"""Minimal async S3 client protocols used by ``S3CompatibleStorage``."""

from __future__ import annotations

from typing import Protocol


class S3Body(Protocol):
    """Streaming body returned by ``get_object``."""

    async def read(self, size: int = -1) -> bytes:
        """Read the next window of object bytes."""


class S3ObjectClient(Protocol):
    """Minimal async S3 client surface used by ``S3CompatibleStorage``."""

    async def put_object(self, **kwargs: object) -> object:
        """Upload an object."""

    async def get_object(self, **kwargs: object) -> dict[str, S3Body]:
        """Download an object."""

    async def delete_object(self, **kwargs: object) -> object:
        """Delete an object."""

    async def head_object(self, **kwargs: object) -> object:
        """Probe object existence."""

    async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """List object keys in the bucket."""

    async def create_multipart_upload(self, **kwargs: object) -> dict[str, object]:
        """Start a multipart upload."""

    async def upload_part(self, **kwargs: object) -> dict[str, object]:
        """Upload one part."""

    async def complete_multipart_upload(self, **kwargs: object) -> object:
        """Finish a multipart upload."""

    async def abort_multipart_upload(self, **kwargs: object) -> object:
        """Abort a multipart upload."""
