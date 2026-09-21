"""Phase 3: quotas, SDK gRPC parity, lifecycle, multipart S3, sweeper."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import grpc
import pytest
from httpx import ASGITransport, AsyncClient
from pixeldive_sdk import GrpcClient, RestClient, sample_session_payload

from app.api import create_app
from app.auth import Principal
from app.config import Settings
from app.exceptions import QuotaExceededError, SessionNotFoundError
from app.grpc_server import start_grpc_server
from app.hash_keys import sha256_hex
from app.models import ImageUpload
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.service import SessionService
from app.storage import LocalFilesystemStorage, S3CompatibleStorage
from tests.conftest import PNG_1X1, sample_create
from tests.factories import auth_settings, make_service
from tests.test_grpc import _create_request
from tests.test_storage import FakeS3


@pytest.mark.asyncio
async def test_cross_tenant_is_not_found(tmp_path: Path) -> None:
    """Wrong-owner access uses the same error as a missing session (SEC-003)."""
    settings = auth_settings(tmp_path)
    service, engine = await make_service(settings)
    owner = Principal(owner_id="tenant-a")
    other = Principal(owner_id="tenant-b")
    created = await service.create_session(sample_create(session_name="owned"), owner)
    with pytest.raises(SessionNotFoundError, match="not found"):
        await service.get_session(created.id, other)
    with pytest.raises(SessionNotFoundError, match="not found"):
        await service.get_session(uuid.uuid4(), owner)
    await engine.dispose()


@pytest.mark.asyncio
async def test_rate_limit_returns_http_429(tmp_path: Path) -> None:
    """The second authenticated request is 429 when the rate cap is 1 (SEC-002)."""
    settings = auth_settings(tmp_path, rate_limit_per_minute=1)
    service, engine = await make_service(settings)
    principal = Principal(owner_id="tenant-a")
    session = await service.create_session(sample_create(), principal)
    app = create_app(service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        limited = await http.get(
            f"/api/v1/sessions/{session.id}",
            headers={"Authorization": "Bearer alpha"},
        )
        assert limited.status_code == 429
        assert limited.json()["detail"] == "rate limit exceeded"
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_byte_quotas_and_auth_off(tmp_path: Path) -> None:
    """Session/tenant byte caps apply only when a principal is present (SEC-002)."""
    settings = auth_settings(
        tmp_path,
        session_max_upload_bytes=len(PNG_1X1),
        tenant_max_upload_bytes=0,
    )
    service, engine = await make_service(settings)
    principal = Principal(owner_id="tenant-a")
    session = await service.create_session(sample_create(), principal)
    image = await service.add_image(
        session.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
        principal,
    )
    assert image.size_bytes == len(PNG_1X1)
    with pytest.raises(QuotaExceededError, match="quota exceeded"):
        await service.add_image(
            session.id,
            ImageUpload(filename="again.png", content_type="image/png", payload=PNG_1X1),
            principal,
        )
    open_settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'open.db'}",
        storage_backend="local",
        storage_root=tmp_path / "open-images",
        auth_required=False,
        rate_limit_per_minute=1,
        session_max_upload_bytes=1,
        log_json=False,
    )
    open_service, open_engine = await make_service(open_settings)
    first = await open_service.create_session(sample_create(session_name="a"))
    second = await open_service.create_session(sample_create(session_name="b"))
    uploaded = await open_service.add_image(
        first.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    assert uploaded.size_bytes == len(PNG_1X1)
    assert first.id != second.id
    tenant_settings = auth_settings(
        tmp_path / "tenant",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'tenant.db'}",
        tenant_max_upload_bytes=len(PNG_1X1),
        session_max_upload_bytes=0,
    )
    tenant_service, tenant_engine = await make_service(tenant_settings)
    one = await tenant_service.create_session(sample_create(session_name="t1"), principal)
    two = await tenant_service.create_session(sample_create(session_name="t2"), principal)
    await tenant_service.add_image(
        one.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
        principal,
    )
    with pytest.raises(QuotaExceededError, match="tenant"):
        await tenant_service.add_image(
            two.id,
            ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
            principal,
        )
    await tenant_service.delete_session(one.id, principal)
    recovered = await tenant_service.add_image(
        two.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
        principal,
    )
    assert recovered.size_bytes == len(PNG_1X1)
    await engine.dispose()
    await open_engine.dispose()
    await tenant_engine.dispose()


@pytest.mark.asyncio
async def test_run_closes_storage_and_sweeper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Shutdown acloses storage and cancels the orphan sweeper (OPS-002, DATA-004)."""
    import app.runtime as runtime

    flags: dict[str, bool] = {}

    class FakeGrpc:
        async def wait_for_termination(self) -> None:
            flags["grpc"] = True

        async def stop(self, grace: object = None) -> None:
            del grace
            flags["stopped"] = True

    class FakeHttp:
        async def serve(self) -> None:
            flags["http"] = True

    class FakeStorage(LocalFilesystemStorage):
        async def aclose(self) -> None:
            flags["closed"] = True

    async def fake_start(*args: object, **kwargs: object) -> tuple[FakeGrpc, int]:
        del args, kwargs
        return FakeGrpc(), 9

    monkeypatch.setattr(runtime, "start_grpc_server", fake_start)
    monkeypatch.setattr(runtime, "build_http_server", lambda app, settings: FakeHttp())
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'run.db'}",
        storage_root=tmp_path / "img",
        storage_backend="local",
        orphan_sweep_interval_seconds=0.05,
        log_json=False,
    )
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runtime, "build_storage", lambda _s: FakeStorage(settings.storage_root))
    await runtime.run(settings)
    assert flags["http"] is True
    assert flags["stopped"] is True
    assert flags["closed"] is True


@pytest.mark.asyncio
async def test_orphan_sweep_loop_and_failures(
    service: SessionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sweeper loop returns when stop is set and swallows sweep errors (DATA-004)."""
    from app.lifecycle import close_storage, orphan_sweep_loop

    stop = asyncio.Event()
    task = asyncio.create_task(orphan_sweep_loop(service, 0.01, stop))
    await asyncio.sleep(0.03)
    stop.set()
    await asyncio.wait_for(task, timeout=1)

    async def boom() -> int:
        raise RuntimeError("sweep failed")

    monkeypatch.setattr(service, "sweep_orphans", boom)
    stop2 = asyncio.Event()
    task2 = asyncio.create_task(orphan_sweep_loop(service, 0.01, stop2))
    await asyncio.sleep(0.03)
    stop2.set()
    await asyncio.wait_for(task2, timeout=1)
    await close_storage(object())


@pytest.mark.asyncio
async def test_grpc_sdk_parity_and_path_upload(service: SessionService, tmp_path: Path) -> None:
    """GrpcClient covers remaining RPCs; both clients stream a file path."""
    server, port = await start_grpc_server(service, "127.0.0.1", 0)
    frame = tmp_path / "frame.png"
    frame.write_bytes(PNG_1X1)
    async with GrpcClient(f"127.0.0.1:{port}") as client:
        session = await client.create_session()
        fetched = await client.get_session(session.id)
        assert fetched.session_name == session.session_name
        updated = await client.update_session(
            session.id,
            {"status": "COMPLETED", "metadata": {"k": "v"}, "session_name": "renamed"},
            merge_metadata=True,
        )
        assert updated.status == "COMPLETED"
        image = await client.upload_image_from_path(
            session.id,
            frame,
            content_type="image/png",
            chunk_size=8,
        )
        assert image.size_bytes == len(PNG_1X1)
        listed = await client.list_images(session.id)
        assert listed.images[0].id == image.id
        payload = b"".join([chunk async for chunk in client.download_image(session.id, image.id)])
        assert payload == PNG_1X1
        batch = await client.upload_images_batch(
            session.id,
            [("b.png", PNG_1X1, "image/png")],
            chunk_size=8,
        )
        assert len(batch) == 1
        from_paths = await client.upload_images_batch_from_paths(
            session.id,
            [(frame, "c.png", "image/png")],
            chunk_size=8,
        )
        assert len(from_paths) == 1
        await client.delete_session(session.id)
    await server.stop(grace=0)

    app = create_app(service)
    transport = ASGITransport(app=app)
    http = AsyncClient(transport=transport, base_url="http://test")
    async with RestClient("http://test", client=http) as rest:
        created = await rest.create_session(sample_session_payload("rest-path"))
        uploaded = await rest.upload_image_from_path(created["id"], frame, metadata='{"iso": 64}')
        assert "storage_path" not in uploaded
        batched = await rest.upload_images_batch_from_paths(
            created["id"],
            [(frame, "batch.png", "image/png")],
            metadata='{"iso": 64}',
        )
        assert len(batched) == 1


def test_chunking_and_update_mapping() -> None:
    """Byte windows and UpdateSessionRequest mapping stay small and explicit."""
    from pixeldive_sdk.chunking import iter_bytes
    from pixeldive_sdk.grpc_mapping import update_session_request

    assert list(iter_bytes(b"", 8)) == [b""]
    assert list(iter_bytes(b"abcd", 2)) == [b"ab", b"cd"]
    request = update_session_request("sid", {"clear_metadata": True, "status": "COMPLETED"})
    assert request.clear_metadata is True
    assert request.status == "COMPLETED"


@pytest.mark.asyncio
async def test_single_image_chunks_empty_stream() -> None:
    """An empty iterator still emits a header chunk so the RPC can reject it."""
    from pixeldive_sdk.grpc_iter import single_image_chunks

    chunks = [chunk async for chunk in single_image_chunks("sid", "x.png", "image/png", [])]
    assert len(chunks) == 1
    assert chunks[0].session_id == "sid"
    assert chunks[0].data == b""


def test_rate_window_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hits older than the window are dropped before counting (SEC-002)."""
    from app.quotas import TenantQuota

    quota = TenantQuota(
        requests_per_window=1, window_seconds=1.0, tenant_max_bytes=0, session_max_bytes=0
    )
    principal = Principal(owner_id="tenant-a")
    times = iter([0.0, 2.0])
    monkeypatch.setattr("app.quotas.time.monotonic", lambda: next(times))
    quota.hit(principal)
    quota.hit(principal)


def test_quota_release_allows_retry() -> None:
    """Failed persists must not keep reserved bytes (SEC-002)."""
    from app.quotas import TenantQuota

    quota = TenantQuota(
        requests_per_window=0,
        window_seconds=60.0,
        tenant_max_bytes=10,
        session_max_bytes=10,
    )
    principal = Principal(owner_id="tenant-a")
    session_id = uuid.uuid4()
    quota.reserve_bytes(principal, session_id, 10)
    with pytest.raises(QuotaExceededError):
        quota.reserve_bytes(principal, session_id, 1)
    quota.release_bytes(principal, session_id, 4)
    quota.reserve_bytes(principal, session_id, 4)
    quota.release_bytes(principal, session_id, 10)
    quota.release_bytes(None, session_id, 10)
    quota.release_bytes(principal, session_id, 0)
    unlimited = TenantQuota(0, 60.0, 0, 0)
    unlimited.reserve_bytes(principal, session_id, 5)
    unlimited.release_bytes(principal, session_id, 5)


@pytest.mark.asyncio
async def test_failed_persist_releases_quota(tmp_path: Path) -> None:
    """A storage failure must not consume the session byte budget."""
    settings = auth_settings(
        tmp_path,
        session_max_upload_bytes=len(PNG_1X1),
        tenant_max_upload_bytes=0,
    )
    service, engine = await make_service(settings)
    principal = Principal(owner_id="tenant-a")
    session = await service.create_session(sample_create(), principal)
    real_save = service._storage.save

    async def boom_save(payload: bytes, content_type: str) -> str:
        del payload, content_type
        raise RuntimeError("disk full")

    service._storage.save = boom_save  # type: ignore[method-assign]
    broken = ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1)
    with pytest.raises(RuntimeError, match="disk full"):
        await service.add_image(session.id, broken, principal)
    with pytest.raises(RuntimeError, match="disk full"):
        await service.add_images_batch(
            session.id,
            [ImageUpload(filename="batch.png", content_type="image/png", payload=PNG_1X1)],
            principal,
        )
    service._storage.save = real_save  # type: ignore[method-assign]
    image = await service.add_image(
        session.id,
        ImageUpload(filename="ok.png", content_type="image/png", payload=PNG_1X1),
        principal,
    )
    assert image.size_bytes == len(PNG_1X1)
    await engine.dispose()


@pytest.mark.asyncio
async def test_grpc_quota_is_resource_exhausted(tmp_path: Path) -> None:
    """Authenticated gRPC maps quota failures to RESOURCE_EXHAUSTED (SEC-002)."""
    settings = auth_settings(tmp_path, rate_limit_per_minute=1, grpc_insecure=True)
    service, engine = await make_service(settings)
    server, port = await start_grpc_server(service, "127.0.0.1", 0)
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = pb_grpc.SessionServiceStub(channel)
    try:
        created = await stub.CreateSession(
            _create_request(),
            metadata=(("authorization", "Bearer alpha"),),
        )
        with pytest.raises(grpc.aio.AioRpcError) as limited:
            await stub.GetSession(
                pb.GetSessionRequest(session_id=created.session.id),
                metadata=(("authorization", "Bearer alpha"),),
            )
        assert limited.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED
    finally:
        await channel.close()
        await server.stop(grace=0)
        await engine.dispose()


@pytest.mark.asyncio
async def test_s3_multipart_chunks_and_abort(tmp_path: Path) -> None:
    """save_file uploads in part_size windows and aborts on failure (PERF-003)."""
    client = FakeS3()
    backend = S3CompatibleStorage(client, bucket="pixeldive", part_size=8)
    source = tmp_path / "frame.png"
    source.write_bytes(PNG_1X1)
    key = await backend.save_file(source, sha256_hex(PNG_1X1), "image/png")
    assert client.objects[key] == PNG_1X1
    assert client.part_sizes
    assert max(client.part_sizes) <= 8
    assert len(client.part_sizes) > 1

    class Boom(FakeS3):
        async def upload_part(self, **kwargs: object) -> dict[str, object]:
            raise RuntimeError("part failed")

    boom = Boom()
    failing = S3CompatibleStorage(boom, bucket="pixeldive", part_size=8)
    with pytest.raises(RuntimeError):
        await failing.save_file(source, sha256_hex(PNG_1X1), "image/png")
    assert boom.aborted

    class BoomAbort(Boom):
        async def abort_multipart_upload(self, **kwargs: object) -> None:
            del kwargs
            raise RuntimeError("abort failed")

    masked = BoomAbort()
    with pytest.raises(RuntimeError, match="part failed"):
        await S3CompatibleStorage(masked, bucket="pixeldive", part_size=8).save_file(
            source,
            sha256_hex(PNG_1X1),
            "image/png",
        )

    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    empty_key = await backend.save_file(empty, sha256_hex(b""), "image/png")
    assert client.objects[empty_key] == b""
    with pytest.raises(ValueError, match="positive"):
        await S3CompatibleStorage(client, bucket="pixeldive", part_size=0).save_file(
            empty,
            sha256_hex(b""),
            "image/png",
        )
