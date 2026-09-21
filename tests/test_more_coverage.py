"""Extra branch coverage for Phase 2 helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import create_app
from app.auth import bearer_token, parse_api_keys
from app.blob_gc import gc_unreferenced, referenced_paths, sweep_orphans
from app.exceptions import ImageTooLargeError
from app.pagination import clamp_limit, next_cursor
from app.s3_listing import age_from_head, contents, mtime
from app.service import SessionService
from app.spool import Spool, SpoolWriter, spool_chunks
from app.uploads import discard_spool
from tests.conftest import JPEG_MIN, PNG_1X1, sample_create


def test_auth_and_pagination_helpers() -> None:
    """Cover remaining parse/clamp branches."""
    with pytest.raises(ValueError, match="object"):
        parse_api_keys("[1]")
    assert parse_api_keys("a:one,, :skip") == {"a": "one"}
    assert bearer_token("Basic x") is None
    assert bearer_token("Bearer   ") is None
    assert clamp_limit(0, 50, 200) == 50
    assert clamp_limit(999, 50, 200) == 200
    items, cursor = next_cursor(["a"], 5, lambda _x: None, lambda _x: None)  # type: ignore[arg-type,return-value]
    assert items == ["a"] and cursor is None


def test_s3_helpers() -> None:
    """list_objects parsing and mtime coercion."""
    assert contents({"Contents": "nope"}) == []
    assert mtime(10) == 10.0
    assert mtime("x") == 0.0
    assert age_from_head({}) == 0.0
    assert age_from_head("nope") == 0.0


@pytest.mark.asyncio
async def test_spool_gc_and_discard(tmp_path: Path, service: SessionService, storage) -> None:
    """Spool abort/delete, empty path GC, and discard missing files."""
    writer = SpoolWriter(tmp_path, max_bytes=8)
    await writer.start()
    await writer.feed(b"")
    with pytest.raises(ImageTooLargeError):
        await writer.feed(b"123456789")
    missing = Spool(tmp_path / "gone.part", "abc", 1)
    await missing.delete()
    await discard_spool(
        __import__("app.models", fromlist=["ImageUpload"]).ImageUpload(
            filename="x.png",
            content_type="image/png",
            spool_path=str(tmp_path / "nope.part"),
        ),
    )
    assert await referenced_paths(service._factory, []) == set()
    await gc_unreferenced(service._factory, storage, [], min_age_seconds=0)
    session = await service.create_session(sample_create(session_name="age"))
    image = await service.add_image(
        session.id,
        __import__("app.models", fromlist=["ImageUpload"]).ImageUpload(
            filename="a.png",
            content_type="image/png",
            payload=PNG_1X1,
        ),
    )
    await gc_unreferenced(
        service._factory,
        storage,
        [image.storage_path],
        min_age_seconds=10_000,
    )
    assert await storage.exists(image.storage_path)
    orphan = await storage.save(JPEG_MIN, "image/jpeg")
    assert await sweep_orphans(service._factory, storage, min_age_seconds=10_000) == 0
    await storage.delete(orphan)

    async def chunks():
        yield PNG_1X1

    spool = await spool_chunks(chunks(), tmp_path, 1024)
    assert spool.size_bytes == len(PNG_1X1)
    await spool.delete()


def test_list_local_blobs_skips_missing_and_dotted(tmp_path: Path) -> None:
    """Incoming spools and missing roots are ignored by the sweeper walk."""
    from app.local_listing import list_local_blobs

    missing = tmp_path / "gone"
    assert list_local_blobs(missing) == []
    hidden = tmp_path / ".incoming"
    hidden.mkdir()
    (hidden / "part").write_bytes(b"x")
    visible = tmp_path / "ab"
    visible.mkdir()
    (visible / "blob.bin").write_bytes(b"y")
    keys = {key for key, _mtime in list_local_blobs(tmp_path)}
    assert keys == {"ab/blob.bin"}


@pytest.mark.asyncio
async def test_list_images_cursor_and_middleware_error(service: SessionService) -> None:
    """Image list pagination and observability exception path."""
    from app.models import ImageUpload

    session = await service.create_session(sample_create(session_name="pages"))
    first = await service.add_image(
        session.id,
        ImageUpload(filename="a.png", content_type="image/png", payload=PNG_1X1),
    )
    second = await service.add_image(
        session.id,
        ImageUpload(filename="b.jpg", content_type="image/jpeg", payload=JPEG_MIN),
    )
    page = await service.list_images(session.id, limit=1)
    assert len(page.items) == 1
    rest = await service.list_images(session.id, limit=1, cursor=page.next_cursor)
    assert {page.items[0].id, rest.items[0].id} == {first.id, second.id}


@pytest.mark.asyncio
async def test_sdk_cursors_owned_client_and_demo_settings(
    service: SessionService, monkeypatch
) -> None:
    """Cover SDK cursor params, owned httpx client, and demo env settings."""
    import httpx
    from httpx import HTTPStatusError, Request, Response
    from pixeldive_sdk.client import RestClient
    from pixeldive_sdk.grpc_client import GrpcClient

    from demo import app as demo_app
    from demo.app import _error_body, create_demo_app

    monkeypatch.setenv("PIXELDIVE_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("PIXELDIVE_TOKEN", "tok")
    assert demo_app._settings()[1] == "tok"
    monkeypatch.setenv("PIXELDIVE_TLS_CA", "/certs/ca.pem")
    assert demo_app._settings()[2] == "/certs/ca.pem"
    monkeypatch.delenv("PIXELDIVE_TLS_CA", raising=False)
    app = create_app(service)
    transport = ASGITransport(app=app)
    http = AsyncClient(transport=transport, base_url="http://test")
    client = RestClient("http://test", token="unused", client=http)
    listed = await client.list_sessions(limit=5)
    assert "items" in listed
    created = await client.create_session(
        __import__("pixeldive_sdk", fromlist=["sample_session_payload"]).sample_session_payload(
            "c"
        ),
    )
    images = await client.list_images(created["id"], cursor=None)
    assert images["items"] == []

    with pytest.raises(httpx.HTTPStatusError):
        await client.list_sessions(limit=1, cursor="%%%")
    with pytest.raises(httpx.HTTPStatusError):
        await client.list_images(created["id"], cursor="%%%")
    await client.aclose()
    grpc = GrpcClient("127.0.0.1:1", token="secret", insecure=False)
    assert grpc._metadata() == [("authorization", "Bearer secret")]
    grpc._channel = None
    await grpc.connect()
    await grpc.aclose()

    owned = RestClient("http://test", token="abc")
    await owned.aclose()

    captured: dict[str, object] = {}

    def fake_insecure(target: str, options: object = None) -> str:
        captured["target"] = target
        captured["options"] = options
        return "channel"

    monkeypatch.setattr("grpc.aio.insecure_channel", fake_insecure)
    from pixeldive_sdk.grpc_channel import open_channel
    from pixeldive_sdk.grpc_options import MAX_MESSAGE_BYTES

    assert open_channel("127.0.0.1:9", insecure=True) == "channel"
    options = captured["options"]
    assert isinstance(options, list)
    assert options[0][1] == MAX_MESSAGE_BYTES

    secure: dict[str, object] = {}

    def fake_creds(**kwargs: object) -> str:
        secure["creds"] = kwargs
        return "tls"

    def fake_secure(target: str, credentials: object, options: object = None) -> str:
        secure["target"] = target
        secure["credentials"] = credentials
        secure["options"] = options
        return "secure-channel"

    monkeypatch.setattr("grpc.ssl_channel_credentials", fake_creds)
    monkeypatch.setattr("grpc.aio.secure_channel", fake_secure)
    assert open_channel("localhost:9", insecure=False, root_certificates=b"ca") == "secure-channel"
    assert secure["creds"] == {
        "root_certificates": b"ca",
        "private_key": None,
        "certificate_chain": None,
    }
    with pytest.raises(ValueError, match="insecure=False"):
        open_channel("127.0.0.1:9", insecure=True, root_certificates=b"ca")
    assert (
        open_channel(
            "127.0.0.1:9",
            insecure=False,
            root_certificates=b"ca",
            ssl_target_name_override="localhost",
        )
        == "secure-channel"
    )
    options = secure["options"]
    assert isinstance(options, list)
    assert ("grpc.ssl_target_name_override", "localhost") in options

    req = Request("GET", "http://x")
    text_err = HTTPStatusError(
        "bad",
        request=req,
        response=Response(500, text="oops"),
    )
    assert _error_body(text_err) == {"detail": "oops"}
    json_err = HTTPStatusError(
        "bad",
        request=req,
        response=Response(400, json={"a": 1}),
    )
    assert _error_body(json_err)["detail"] == {"a": 1}
    nested = HTTPStatusError(
        "bad",
        request=req,
        response=Response(404, json={"detail": "missing"}),
    )
    assert _error_body(nested) == {"detail": "missing"}
    demo = create_demo_app()
    async with demo.router.lifespan_context(demo):
        assert demo.state.client is not None


def test_json_log_exception_and_demo_main(monkeypatch) -> None:
    """JSON formatter includes exc; demo.main wires uvicorn."""
    from app.observability import JsonLogFormatter

    record = logging.LogRecord("pixeldive", logging.ERROR, __file__, 1, "fail", None, None)
    try:
        raise RuntimeError("x")
    except RuntimeError:
        record.exc_info = __import__("sys").exc_info()
    line = JsonLogFormatter().format(record)
    assert "RuntimeError" in line

    import demo.__main__ as demo_main

    captured: dict[str, object] = {}

    def fake_run(app, host, port, log_level):
        captured["host"] = host
        captured["port"] = port
        captured["app"] = app

    monkeypatch.setattr(demo_main.uvicorn, "run", fake_run)
    monkeypatch.setenv("DEMO_HTTP_PORT", "8099")
    demo_main.main()
    assert captured["port"] == 8099
