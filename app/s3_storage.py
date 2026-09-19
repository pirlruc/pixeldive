"""S3-compatible blob backend for SessionService."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from app.hash_keys import object_key, sha256_hex
from app.s3_client import default_s3_client
from app.s3_listing import age_from_head, contents, is_missing, mtime
from app.s3_pages import iter_list_pages
from app.s3_stream import iter_body
from app.s3_types import S3ObjectClient

__all__ = [
    "S3CompatibleStorage",
    "S3ObjectClient",
    "default_s3_client",
    "is_missing",
]


class S3CompatibleStorage:
    """SHA-256 keys in an S3-compatible bucket (MinIO, AWS, GCS XML API)."""

    def __init__(self, client: S3ObjectClient, bucket: str) -> None:
        """Bind an async S3 client to ``bucket``."""
        self._client = client
        self._bucket = bucket

    async def _put(self, key: str, payload: bytes, content_type: str) -> None:
        """PUT bytes under ``key``."""
        await self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )

    async def save(self, payload: bytes, content_type: str) -> str:
        """PUT the object (idempotent; no HEAD round trip)."""
        key = object_key(sha256_hex(payload), content_type)
        await self._put(key, payload, content_type)
        return key

    async def save_file(self, source: Path, digest_hex: str, content_type: str) -> str:
        """PUT a spool file using the precomputed digest as the object key."""
        key = object_key(digest_hex, content_type)
        async with aiofiles.open(source, "rb") as handle:
            payload = await handle.read()
        await self._put(key, payload, content_type)
        return key

    async def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Download the object and yield it in chunks."""
        response = await self._client.get_object(Bucket=self._bucket, Key=storage_path)
        async for chunk in iter_body(response["Body"], chunk_size):
            yield chunk

    async def delete(self, storage_path: str) -> None:
        """Delete the object; S3 delete is idempotent."""
        await self._client.delete_object(Bucket=self._bucket, Key=storage_path)

    async def _head(self, storage_path: str) -> object | None:
        """HEAD an object; missing keys return None."""
        try:
            return await self._client.head_object(Bucket=self._bucket, Key=storage_path)
        except Exception as exc:  # noqa: BLE001 — botocore ClientError is optional
            if is_missing(exc):
                return None
            raise

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
