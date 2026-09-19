"""Local filesystem and S3-compatible storage backends."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage import LocalFilesystemStorage, S3CompatibleStorage, object_key, sha256_hex
from tests.conftest import PNG_1X1


class FakeS3:
    """In-memory boto3-like client for S3CompatibleStorage tests."""

    def __init__(self) -> None:
        """Start with an empty bucket dict."""
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def put_object(self, **kwargs: object) -> None:
        """Store Body under Key."""
        key = str(kwargs["Key"])
        self.objects[key] = bytes(kwargs["Body"])  # type: ignore[arg-type]
        self.content_types[key] = str(kwargs.get("ContentType", ""))

    def get_object(self, **kwargs: object) -> dict[str, object]:
        """Return a file-like Body."""
        key = str(kwargs["Key"])
        payload = self.objects[key]
        return {"Body": _BytesReader(payload)}

    def delete_object(self, **kwargs: object) -> None:
        """Drop Key if present."""
        self.objects.pop(str(kwargs["Key"]), None)

    def head_object(self, **kwargs: object) -> dict[str, str]:
        """Raise a 404-like error when missing."""
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise _Missing()
        return {"Key": key}


class _BytesReader:
    """Minimal streaming Body for FakeS3.get_object."""

    def __init__(self, payload: bytes) -> None:
        """Wrap bytes."""
        self._payload = payload
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        """Read the next window."""
        if size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class _Missing(Exception):
    """Stand-in for botocore ClientError 404."""

    response = {"Error": {"Code": "404"}}


@pytest.mark.asyncio
async def test_local_save_is_content_addressed(tmp_path: Path) -> None:
    """Identical payloads reuse the same relative key."""
    backend = LocalFilesystemStorage(tmp_path)
    first = await backend.save(PNG_1X1, "image/png")
    second = await backend.save(PNG_1X1, "image/png")
    assert first == second
    assert first == object_key(sha256_hex(PNG_1X1), "image/png")
    assert (tmp_path / first).is_file()


@pytest.mark.asyncio
async def test_local_stream_and_delete(tmp_path: Path) -> None:
    """Streaming yields the original bytes; delete removes the file."""
    backend = LocalFilesystemStorage(tmp_path)
    key = await backend.save(PNG_1X1, "image/png")
    chunks = [chunk async for chunk in backend.stream(key, chunk_size=8)]
    assert b"".join(chunks) == PNG_1X1
    await backend.delete(key)
    assert not await backend.exists(key)
    await backend.delete(key)


@pytest.mark.asyncio
async def test_replace_races(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FileExistsError and recoverable FileNotFoundError are handled."""
    backend = LocalFilesystemStorage(tmp_path)
    import aiofiles.os as aio_os

    async def exists_err(src: object, dst: object) -> None:
        del src, dst
        raise FileExistsError

    monkeypatch.setattr(aio_os, "replace", exists_err)
    key = await backend.save(PNG_1X1, "image/png")
    assert key.endswith(".png")

    async def missing_but_present(src: object, dst: object) -> None:
        Path(dst).write_bytes(PNG_1X1)
        raise FileNotFoundError

    monkeypatch.setattr(aio_os, "replace", missing_but_present)
    key2 = await backend.save(b"other-bytes-not-png-hash", "image/png")
    assert key2.endswith(".png")


@pytest.mark.asyncio
async def test_replace_missing_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FileNotFoundError is re-raised when the destination was never created."""
    backend = LocalFilesystemStorage(tmp_path)
    import aiofiles.os as aio_os

    async def gone(src: object, dst: object) -> None:
        del src, dst
        raise FileNotFoundError

    monkeypatch.setattr(aio_os, "replace", gone)
    with pytest.raises(FileNotFoundError):
        await backend.save(b"unique-payload-for-missing-dest", "image/png")


@pytest.mark.asyncio
async def test_local_rejects_path_escape(tmp_path: Path) -> None:
    """Resolved keys must stay under the storage root."""
    backend = LocalFilesystemStorage(tmp_path)
    with pytest.raises(FileNotFoundError):
        async for _ in backend.stream("../secret", chunk_size=8):
            pass
    assert await backend.exists("../secret") is False
    await backend.delete("../secret")


@pytest.mark.asyncio
async def test_s3_exists_reraises_unexpected() -> None:
    """Non-404 HEAD failures propagate."""

    class Boom(FakeS3):
        def head_object(self, **kwargs: object) -> dict[str, str]:
            raise RuntimeError("timeout")

    backend = S3CompatibleStorage(Boom(), bucket="pixeldive")
    with pytest.raises(RuntimeError):
        await backend.exists("nope")


def test_unknown_content_type_uses_bin_extension() -> None:
    """Unrecognized types fall back to ``.bin``."""
    from app.hash_keys import object_key, sha256_hex

    key = object_key(sha256_hex(b"abc"), "application/octet-stream")
    assert key.endswith(".bin")


@pytest.mark.asyncio
async def test_s3_adapter_round_trip() -> None:
    """S3CompatibleStorage talks to a boto3-shaped client."""
    client = FakeS3()
    backend = S3CompatibleStorage(client, bucket="pixeldive")
    key = await backend.save(PNG_1X1, "image/png")
    assert await backend.exists(key)
    again = await backend.save(PNG_1X1, "image/png")
    assert again == key
    payload = b"".join([chunk async for chunk in backend.stream(key, chunk_size=32)])
    assert payload == PNG_1X1
    await backend.delete(key)
    assert not await backend.exists(key)
