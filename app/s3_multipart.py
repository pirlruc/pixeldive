"""Multipart upload of a spool file so save_file stays O(chunk) (PERF-003)."""

from __future__ import annotations

import logging
from pathlib import Path

import aiofiles

from app.s3_types import S3ObjectClient

logger = logging.getLogger("pixeldive")


async def put_file_multipart(
    client: S3ObjectClient,
    *,
    bucket: str,
    key: str,
    source: Path,
    content_type: str,
    part_size: int,
) -> None:
    """Upload ``source`` as S3 multipart parts of ``part_size`` bytes."""
    if part_size <= 0:
        msg = "part_size must be positive"
        raise ValueError(msg)
    upload_id = await _start(client, bucket=bucket, key=key, content_type=content_type)
    try:
        parts = await _upload_parts(
            client,
            bucket=bucket,
            key=key,
            upload_id=upload_id,
            source=source,
            part_size=part_size,
        )
        await _complete(client, bucket=bucket, key=key, upload_id=upload_id, parts=parts)
    except BaseException:
        await _abort(client, bucket=bucket, key=key, upload_id=upload_id)
        raise


async def _start(client: S3ObjectClient, *, bucket: str, key: str, content_type: str) -> str:
    """Create a multipart upload and return its UploadId."""
    response = await client.create_multipart_upload(
        Bucket=bucket,
        Key=key,
        ContentType=content_type,
    )
    return str(response["UploadId"])


async def _upload_parts(
    client: S3ObjectClient,
    *,
    bucket: str,
    key: str,
    upload_id: str,
    source: Path,
    part_size: int,
) -> list[dict[str, object]]:
    """Read ``source`` in ``part_size`` windows and upload each part."""
    parts: list[dict[str, object]] = []
    async with aiofiles.open(source, "rb") as handle:
        number = 1
        while True:
            chunk = await handle.read(part_size)
            if not chunk and parts:
                break
            response = await client.upload_part(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=number,
                Body=chunk,
            )
            parts.append({"ETag": response["ETag"], "PartNumber": number})
            number += 1
            if not chunk:
                break
    return parts


async def _complete(
    client: S3ObjectClient,
    *,
    bucket: str,
    key: str,
    upload_id: str,
    parts: list[dict[str, object]],
) -> None:
    """Finish a multipart upload."""
    await client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


async def _abort(client: S3ObjectClient, *, bucket: str, key: str, upload_id: str) -> None:
    """Best-effort abort; never mask the original upload failure."""
    try:
        await client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
    except Exception:
        logger.exception("abort multipart failed upload_id=%s key=%s", upload_id, key)
