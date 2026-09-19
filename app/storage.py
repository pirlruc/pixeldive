"""Content-addressed image storage: local filesystem or S3-compatible blobs."""

from collections.abc import AsyncIterator, Callable
from typing import Protocol

from app.config import Settings
from app.hash_keys import object_key, sha256_hex
from app.local_storage import LocalFilesystemStorage
from app.s3_storage import S3CompatibleStorage, S3ObjectClient, default_s3_client, is_missing

_default_s3_client = default_s3_client
_is_missing = is_missing

__all__ = [
    "LocalFilesystemStorage",
    "S3CompatibleStorage",
    "S3ObjectClient",
    "StorageBackend",
    "build_storage",
    "object_key",
    "sha256_hex",
]


class StorageBackend(Protocol):
    """Blob store used by SessionService (local disk or S3)."""

    async def save(self, payload: bytes, content_type: str) -> str:
        """Persist bytes and return a backend-relative storage path."""

    def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Yield file bytes in ``chunk_size`` windows."""

    async def delete(self, storage_path: str) -> None:
        """Remove the blob if it exists (missing is not an error)."""

    async def exists(self, storage_path: str) -> bool:
        """Return whether ``storage_path`` is present."""


def build_storage(
    settings: Settings,
    s3_factory: Callable[[Settings], S3ObjectClient] | None = None,
) -> StorageBackend:
    """Construct the configured storage backend."""
    if settings.storage_backend == "local":
        settings.storage_root.mkdir(parents=True, exist_ok=True)
        return LocalFilesystemStorage(settings.storage_root)
    factory = s3_factory or default_s3_client
    return S3CompatibleStorage(factory(settings), settings.s3_bucket)
