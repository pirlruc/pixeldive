"""S3-compatible blob backend for SessionService."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol, cast

from app.config import Settings
from app.hash_keys import object_key, sha256_hex


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


class S3CompatibleStorage:
    """SHA-256 keys in an S3-compatible bucket (MinIO, AWS, GCS XML API)."""

    def __init__(self, client: S3ObjectClient, bucket: str) -> None:
        """Bind a boto3-like client to ``bucket``."""
        self._client = client
        self._bucket = bucket

    async def save(self, payload: bytes, content_type: str) -> str:
        """PUT the object unless a HEAD shows it already exists."""
        key = object_key(sha256_hex(payload), content_type)
        if await self.exists(key):
            return key
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
        return key

    async def stream(self, storage_path: str, chunk_size: int) -> AsyncIterator[bytes]:
        """Download the object and yield it in chunks."""
        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=storage_path,
        )
        body = response["Body"]
        reader = body.read
        while True:
            chunk = await asyncio.to_thread(reader, chunk_size)
            if not chunk:
                break
            yield chunk

    async def delete(self, storage_path: str) -> None:
        """Delete the object; S3 delete is idempotent."""
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=storage_path,
        )

    async def exists(self, storage_path: str) -> bool:
        """HEAD the object; treat 404 as missing."""
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=storage_path,
            )
        except Exception as exc:  # noqa: BLE001 — boto3 ClientError is optional
            if is_missing(exc):
                return False
            raise
        return True


def is_missing(exc: BaseException) -> bool:
    """Return True for S3 404 / NotFound client errors."""
    response = getattr(exc, "response", None) if hasattr(exc, "response") else None
    status = None
    if isinstance(response, dict):
        status = response.get("Error", {}).get("Code")
    if status in {"404", "NotFound", "NoSuchKey"}:
        return True
    name = type(exc).__name__
    return name in {"NoSuchKey", "ClientError"} and "404" in str(exc)


def default_s3_client(settings: Settings) -> S3ObjectClient:
    """Build a boto3 client; imported lazily so local-only deploys skip boto3."""
    import boto3

    return cast(
        S3ObjectClient,
        boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ),
    )
