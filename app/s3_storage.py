"""S3-compatible blob backend for SessionService."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

from app.config import Settings
from app.hash_keys import object_key, sha256_hex
from app.s3_listing import age_from_head, contents, is_missing, mtime
from app.s3_types import S3ObjectClient


class S3CompatibleStorage:
    """SHA-256 keys in an S3-compatible bucket (MinIO, AWS, GCS XML API)."""

    def __init__(self, client: S3ObjectClient, bucket: str) -> None:
        """Bind a boto3-like client to ``bucket``."""
        self._client = client
        self._bucket = bucket

    async def save(self, payload: bytes, content_type: str) -> str:
        """PUT the object on a worker thread (idempotent; no HEAD round trip)."""
        key = object_key(sha256_hex(payload), content_type)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
        return key

    def _put_file(self, source: Path, key: str, content_type: str) -> None:
        """Upload a local file handle without loading it fully in-process."""
        with source.open("rb") as handle:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=handle,
                ContentType=content_type,
            )

    async def save_file(self, source: Path, digest_hex: str, content_type: str) -> str:
        """PUT a spool file using the precomputed digest as the object key."""
        key = object_key(digest_hex, content_type)
        await asyncio.to_thread(self._put_file, source, key, content_type)
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

    async def list_blobs(self) -> list[tuple[str, float]]:
        """Page through ``list_objects_v2`` and return keys with mtimes."""
        blobs: list[tuple[str, float]] = []
        token: object | None = None
        while True:
            kwargs: dict[str, object] = {"Bucket": self._bucket}
            if token:
                kwargs["ContinuationToken"] = token
            response = await asyncio.to_thread(self._client.list_objects_v2, **kwargs)
            for item in contents(response):
                blobs.append((str(item["Key"]), mtime(item.get("LastModified"))))
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
            if not token:
                break
        return blobs

    async def age_seconds(self, storage_path: str) -> float:
        """HEAD LastModified; missing objects are age 0."""
        try:
            response = await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=storage_path,
            )
        except Exception as exc:  # noqa: BLE001 — boto3 ClientError is optional
            if is_missing(exc):
                return 0.0
            raise
        return age_from_head(response)


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
