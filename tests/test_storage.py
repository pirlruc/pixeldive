"""Local filesystem and S3-compatible storage backends."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.storage import LocalFilesystemStorage, S3CompatibleStorage, object_key, sha256_hex
from tests.conftest import PNG_1X1


class FakeS3:
    """In-memory async S3 client for S3CompatibleStorage tests."""

    def __init__(self, page_size: int | None = None) -> None:
        """Start with an empty bucket dict."""
        self.page_size = page_size
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.mtimes: dict[str, datetime] = {}
        self.last_body: _BytesReader | None = None

    async def put_object(self, **kwargs: object) -> None:
        """Store Body under Key."""
        key = str(kwargs["Key"])
        self.objects[key] = bytes(kwargs["Body"])
        self.content_types[key] = str(kwargs.get("ContentType", ""))
        self.mtimes[key] = datetime.now(UTC)

    async def get_object(self, **kwargs: object) -> dict[str, object]:
        """Return a file-like Body."""
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise _Missing()
        payload = self.objects[key]
        reader = _BytesReader(payload)
        self.last_body = reader
        return {"Body": reader}

    async def delete_object(self, **kwargs: object) -> None:
        """Drop Key if present."""
        key = str(kwargs["Key"])
        self.objects.pop(key, None)
        self.mtimes.pop(key, None)

    async def head_object(self, **kwargs: object) -> dict[str, object]:
        """Raise a 404-like error when missing."""
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise _Missing()
        return {"Key": key, "LastModified": self.mtimes.get(key, datetime.now(UTC))}

    async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """Return stored keys, optionally paginated."""
        keys = sorted(self.objects)
        token = kwargs.get("ContinuationToken")
        start = int(str(token)) if token else 0
        size = self.page_size if self.page_size is not None else max(len(keys), 1)
        page = keys[start : start + size]
        listed = [{"Key": key, "LastModified": self.mtimes[key]} for key in page]
        truncated = start + size < len(keys)
        result: dict[str, object] = {"Contents": listed, "IsTruncated": truncated}
        if truncated:
            result["NextContinuationToken"] = str(start + size)
        return result


class _BytesReader:
    """Minimal streaming Body for FakeS3.get_object."""

    def __init__(self, payload: bytes) -> None:
        """Wrap bytes."""
        self._payload = payload
        self._offset = 0
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        """Read the next window."""
        if size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        """Mark the body closed."""
        self.closed = True


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

    async def exists_and_present(src: object, dst: object) -> None:
        Path(dst).write_bytes(PNG_1X1)
        raise FileExistsError

    monkeypatch.setattr(aio_os, "replace", exists_and_present)
    key = await backend.save(PNG_1X1, "image/png")
    assert key.endswith(".png")
    assert (tmp_path / key).is_file()

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
async def test_replace_exists_without_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FileExistsError is re-raised when the destination was never created."""
    backend = LocalFilesystemStorage(tmp_path)
    import aiofiles.os as aio_os

    async def exists_gone(src: object, dst: object) -> None:
        del src, dst
        raise FileExistsError

    monkeypatch.setattr(aio_os, "replace", exists_gone)
    with pytest.raises(FileExistsError):
        await backend.save(b"unique-payload-for-exists-missing-dest", "image/png")


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
        async def head_object(self, **kwargs: object) -> dict[str, str]:
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
    """S3CompatibleStorage talks to an async S3-shaped client."""
    client = FakeS3()
    backend = S3CompatibleStorage(client, bucket="pixeldive")
    key = await backend.save(PNG_1X1, "image/png")
    assert await backend.exists(key)
    again = await backend.save(PNG_1X1, "image/png")
    assert again == key
    payload = b"".join([chunk async for chunk in backend.stream(key, chunk_size=32)])
    assert payload == PNG_1X1
    assert client.last_body is not None and client.last_body.closed is True
    await backend.delete(key)
    assert not await backend.exists(key)


@pytest.mark.asyncio
async def test_s3_save_file_and_list_blobs(tmp_path: Path) -> None:
    """save_file streams a path; list_blobs returns keys."""
    client = FakeS3()
    backend = S3CompatibleStorage(client, bucket="pixeldive")
    source = tmp_path / "frame.png"
    source.write_bytes(PNG_1X1)
    digest = sha256_hex(PNG_1X1)
    key = await backend.save_file(source, digest, "image/png")
    blobs = await backend.list_blobs()
    assert blobs[0][0] == key
    assert await backend.age_seconds(key) >= 0
    assert await backend.age_seconds("missing") == 0.0


@pytest.mark.asyncio
async def test_s3_list_blobs_paginates() -> None:
    """list_objects_v2 continuation tokens are followed."""
    client = FakeS3(page_size=1)
    backend = S3CompatibleStorage(client, bucket="pixeldive")
    first = await backend.save(b"page-one", "image/png")
    second = await backend.save(b"page-two", "image/png")
    keys = sorted(item[0] for item in await backend.list_blobs())
    assert keys == sorted([first, second])


@pytest.mark.asyncio
async def test_s3_list_blobs_stops_without_token() -> None:
    """Truncated pages without NextContinuationToken end the loop."""

    class Truncated(FakeS3):
        async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            del kwargs
            return {"Contents": [{"Key": "only", "LastModified": 1.0}], "IsTruncated": True}

    blobs = await S3CompatibleStorage(Truncated(), bucket="pixeldive").list_blobs()
    assert blobs == [("only", 1.0)]


@pytest.mark.asyncio
async def test_s3_age_seconds_reraises_unexpected() -> None:
    """Non-404 HEAD failures propagate from age_seconds."""

    class Boom(FakeS3):
        async def head_object(self, **kwargs: object) -> dict[str, str]:
            raise RuntimeError("timeout")

    backend = S3CompatibleStorage(Boom(), bucket="pixeldive")
    with pytest.raises(RuntimeError):
        await backend.age_seconds("nope")


@pytest.mark.asyncio
async def test_aio_s3_adapter_lazy_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """AioS3Adapter opens aiobotocore once and reuses the client."""
    captured: dict[str, object] = {}
    calls = {"put": 0}

    class FakeClient:
        async def put_object(self, **kwargs: object) -> str:
            calls["put"] += 1
            captured["put"] = kwargs
            return "ok"

        async def get_object(self, **kwargs: object) -> dict[str, object]:
            return {"Body": _BytesReader(b"x"), "args": kwargs}

        async def delete_object(self, **kwargs: object) -> str:
            captured["delete"] = kwargs
            return "deleted"

        async def head_object(self, **kwargs: object) -> dict[str, object]:
            return {"Key": str(kwargs["Key"])}

        async def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            return {"Contents": [], "args": kwargs}

    class FakeCM:
        async def __aenter__(self) -> FakeClient:
            captured["entered"] = True
            return FakeClient()

        async def __aexit__(self, *_exc: object) -> None:
            captured["exited"] = True

    class FakeSession:
        def create_client(self, service_name: str, **kwargs: object) -> FakeCM:
            captured["service"] = service_name
            captured.update(kwargs)
            return FakeCM()

    monkeypatch.setattr("aiobotocore.session.get_session", lambda: FakeSession())
    from app.config import Settings
    from app.s3_client import AioS3Adapter, default_s3_client

    settings = Settings(
        storage_backend="s3",
        s3_endpoint_url="http://127.0.0.1:9000",
        s3_bucket="b",
        aws_access_key_id="k",
        aws_secret_access_key="s",
    )
    adapter = default_s3_client(settings)
    assert isinstance(adapter, AioS3Adapter)
    await adapter.aclose()
    await adapter.put_object(Bucket="b", Key="k", Body=b"x")
    await adapter.put_object(Bucket="b", Key="k2", Body=b"y")
    await adapter.get_object(Bucket="b", Key="k")
    await adapter.head_object(Bucket="b", Key="k")
    await adapter.list_objects_v2(Bucket="b")
    await adapter.delete_object(Bucket="b", Key="k")
    assert calls["put"] == 2
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "http://127.0.0.1:9000"
    await adapter.aclose()
    assert captured["exited"] is True


@pytest.mark.asyncio
async def test_aio_s3_adapter_concurrent_ensure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two first calls share one client after the lock."""
    from app.config import Settings
    from app.s3_client import AioS3Adapter

    opened = {"n": 0}

    class FakeClient:
        async def head_object(self, **kwargs: object) -> dict[str, object]:
            return {"Key": str(kwargs["Key"])}

    class FakeCM:
        async def __aenter__(self) -> FakeClient:
            opened["n"] += 1
            await asyncio.sleep(0.01)
            return FakeClient()

        async def __aexit__(self, *_exc: object) -> None:
            return None

    class FakeSession:
        def create_client(self, service_name: str, **kwargs: object) -> FakeCM:
            del service_name, kwargs
            return FakeCM()

    monkeypatch.setattr("aiobotocore.session.get_session", lambda: FakeSession())
    adapter = AioS3Adapter(Settings(storage_backend="s3"))
    await asyncio.gather(adapter.head_object(Key="a"), adapter.head_object(Key="b"))
    assert opened["n"] == 1
    await adapter.aclose()


@pytest.mark.asyncio
async def test_local_save_file_and_list_blobs(tmp_path: Path) -> None:
    """Local save_file copies a spool; list_blobs skips hidden paths."""
    backend = LocalFilesystemStorage(tmp_path)
    source = tmp_path / "frame.png"
    source.write_bytes(PNG_1X1)
    key = await backend.save_file(source, sha256_hex(PNG_1X1), "image/png")
    hidden = tmp_path / ".incoming"
    hidden.mkdir()
    (hidden / "partial.part").write_bytes(b"tmp")
    blobs = await backend.list_blobs()
    keys = [item[0] for item in blobs]
    assert key in keys
    assert not any(item.startswith(".incoming") for item in keys)
    assert await backend.age_seconds(key) >= 0


@pytest.mark.asyncio
async def test_s3_stream_missing_is_file_not_found() -> None:
    """S3 404 on GET maps to FileNotFoundError like the local backend."""
    backend = S3CompatibleStorage(FakeS3(), bucket="pixeldive")
    with pytest.raises(FileNotFoundError):
        async for _ in backend.stream("missing", chunk_size=8):
            pass


@pytest.mark.asyncio
async def test_s3_stream_reraises_unexpected() -> None:
    """Non-404 GET failures propagate from stream."""

    class Boom(FakeS3):
        async def get_object(self, **kwargs: object) -> dict[str, object]:
            raise RuntimeError("timeout")

    backend = S3CompatibleStorage(Boom(), bucket="pixeldive")
    with pytest.raises(RuntimeError):
        async for _ in backend.stream("k", chunk_size=8):
            pass


@pytest.mark.asyncio
async def test_iter_body_closes_async_and_sync() -> None:
    """iter_body closes bodies that expose aclose or close."""
    from app.s3_stream import close_body, iter_body

    closed = {"async": 0, "sync": 0}

    class AsyncBody:
        async def read(self, size: int = -1) -> bytes:
            del size
            return b""

        async def aclose(self) -> None:
            closed["async"] += 1

    class SyncBody:
        def __init__(self) -> None:
            self._sent = False

        async def read(self, size: int = -1) -> bytes:
            del size
            if self._sent:
                return b""
            self._sent = True
            return b"xy"

        def close(self) -> None:
            closed["sync"] += 1

    async for _ in iter_body(AsyncBody(), 8):
        pass
    chunks = [chunk async for chunk in iter_body(SyncBody(), 8)]
    assert chunks == [b"xy"]
    assert closed == {"async": 1, "sync": 1}
    await close_body(object())
