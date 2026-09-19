"""Minimal S3 client protocols used by ``S3CompatibleStorage``."""

from __future__ import annotations

from typing import Protocol


class S3Body(Protocol):
    """Streaming body returned by ``get_object``."""

    def read(self, size: int = -1) -> bytes:
        """Read the next window of object bytes."""


class S3ObjectClient(Protocol):
    """Minimal S3 client surface used by ``S3CompatibleStorage``."""

    def put_object(self, **kwargs: object) -> object:
        """Upload an object."""

    def get_object(self, **kwargs: object) -> dict[str, S3Body]:
        """Download an object."""

    def delete_object(self, **kwargs: object) -> object:
        """Delete an object."""

    def head_object(self, **kwargs: object) -> object:
        """Probe object existence."""

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """List object keys in the bucket."""
