"""S3-compatible blob backend for SessionService."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from app.blobs.hash_keys import object_key, sha256_hex
from app.blobs.s3_client import default_s3_client
from app.blobs.s3_listing import age_from_head, contents, is_missing, missing_or_raise, mtime
from app.blobs.s3_multipart import put_file_multipart
from app.blobs.s3_pages import iter_list_pages
from app.blobs.s3_stream import iter_body
from app.blobs.s3_types import S3ObjectClient

__all__ = [
    "S3CompatibleStorage",
    "S3ObjectClient",
    "default_s3_client",
    "is_missing",
]


class S3CompatibleStorage:
    """SHA-256 keys in an S3-compatible bucket (MinIO, AWS, GCS XML API)."""

    def __init__(
        self,
        client: S3ObjectClient,
        bucket: str,
        *,
        part_size: int = 8 * 1024 * 1024,
        known_limit: int = 4096,
    ) -> None:
        """Bind an async S3 client to ``bucket``."""
        self._client = client
        self._bucket = bucket
        self._part_size = part_size
        self._known: set[str] = set()
        self._known_limit = known_limit

    async def _put(self, key: str, payload: bytes, content_type: str) -> None:
        """PUT bytes under ``key``."""
        await self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )

    async def save(self, payload: bytes, content_type: str) -> str:
        """PUT the object unless this process can still see the same key."""
        key = object_key(sha256_hex(payload), content_type)
        return await self._store_once(key, lambda: self._put(key, payload, content_type))

    async def save_file(self, source: Path, digest_hex: str, content_type: str) -> str:
        """Multipart-PUT a spool unless this process can still see that key."""
        key = object_key(digest_hex, content_type)

        async def write() -> None:
            await put_file_multipart(
                self._client,
                bucket=self._bucket,
                key=key,
                source=source,
                content_type=content_type,
                part_size=self._part_size,
            )

        return await self._store_once(key, write)

    async def _store_once(self, key: str, write: Callable[[], Awaitable[None]]) -> str:
        """Skip a repeat PUT only when a HEAD still sees the object."""
        if await self._still_stored(key):
            return key
        await write()
        self._remember(key)
        return key

    async def _still_stored(self, key: str) -> bool:
        """True when the remember-set hit and the object is still in the bucket."""
        return key in self._known and await self.exists(key)

    def _remember(self, key: str) -> None:
        """Remember ``key``, clearing the set when it reaches ``known_limit``."""
        if len(self._known) >= self._known_limit:
            self._known.clear()
        self._known.add(key)

    async def aclose(self) -> None:
        """Close the underlying client when it exposes ``aclose``."""
        closer = getattr(self._client, "aclose", None)
        if closer is not None:
            await closer()

    async def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Download the object and yield it in chunks."""
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=storage_path)
        except Exception as exc:  # noqa: BLE001 — botocore ClientError is optional
            missing_or_raise(exc)
            raise FileNotFoundError(storage_path) from exc
        async for chunk in iter_body(response["Body"], chunk_size):
            yield chunk

    async def delete(self, storage_path: str) -> None:
        """Delete the object; S3 delete is idempotent."""
        await self._client.delete_object(Bucket=self._bucket, Key=storage_path)
        self._known.discard(storage_path)

    async def _head(self, storage_path: str) -> object | None:
        """HEAD an object; missing keys return None."""
        try:
            return await self._client.head_object(Bucket=self._bucket, Key=storage_path)
        except Exception as exc:  # noqa: BLE001 — botocore ClientError is optional
            missing_or_raise(exc)
            return None

    async def exists(self, storage_path: str) -> bool:
        """HEAD the object; treat 404 as missing."""
        return await self._head(storage_path) is not None

    async def list_blobs(self) -> list[tuple[str, float]]:
        """Page through ``list_objects_v2`` and return keys with mtimes."""
        blobs: list[tuple[str, float]] = []
        async for response in iter_list_pages(self._list_page):
            for item in contents(response):
                blobs.append((str(item["Key"]), mtime(item.get("LastModified"))))
        return blobs

    async def _list_page(self, token: object | None) -> dict[str, object]:
        """Fetch one list_objects_v2 page."""
        kwargs: dict[str, object] = {"Bucket": self._bucket}
        if token:
            kwargs["ContinuationToken"] = token
        return await self._client.list_objects_v2(**kwargs)

    async def age_seconds(self, storage_path: str) -> float:
        """HEAD LastModified; missing objects are age 0."""
        response = await self._head(storage_path)
        return age_from_head(response) if response is not None else 0.0
