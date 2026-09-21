"""Coverage for error-map completeness, production auth, and SDK token headers."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pixeldive_sdk import RestClient, sample_session_payload

from app.blobs.magic import header_bytes, matches_declared_type
from app.config import Settings
from app.error_map import ERROR_STATUS
from app.exceptions import ImageNotFoundError, SessionServiceError
from app.models import ImageUpload
from app.rest.api import create_app
from app.runtime import validate_auth_settings
from app.sessions.auth import Principal, lookup_owner
from app.sessions.service import SessionService
from tests.conftest import JPEG_MIN, PNG_1X1, sample_create
from tests.factories import auth_settings, make_service


def test_error_map_covers_every_domain_error() -> None:
    """REST and gRPC share one table that lists every SessionServiceError."""
    production = {
        cls for cls in SessionServiceError.__subclasses__() if cls.__module__ == "app.exceptions"
    }
    assert set(ERROR_STATUS) == production


def test_lookup_owner_is_constant_time_membership() -> None:
    """Unknown tokens miss; matching tokens return the mapped owner."""
    keys = {"alpha": "tenant-a", "beta": "tenant-b"}
    assert lookup_owner("alpha", keys) == "tenant-a"
    assert lookup_owner("missing", keys) is None
    assert lookup_owner("toolong", keys) is None
    assert lookup_owner("alph", keys) is None


def test_lookup_owner_rejects_null_padded_prefix() -> None:
    """Length is part of the compare so a shorter token cannot match."""
    keys = {"alpha": "tenant-a"}
    assert lookup_owner("alpha\0", keys) is None


def test_default_bind_is_loopback() -> None:
    """Host-native defaults listen on localhost; containers override to 0.0.0.0."""
    assert Settings.model_fields["http_host"].default == "127.0.0.1"
    assert Settings.model_fields["grpc_host"].default == "127.0.0.1"


def test_magic_bytes_match_declared_types(tmp_path: Path) -> None:
    """Sniff PNG/JPEG/WEBP/HEIF/BMP/TIFF; reject forged Content-Type."""
    webp = b"RIFF\x00\x00\x00\x00WEBP"
    heif = b"\x00\x00\x00\x18ftypmif1"
    spool = tmp_path / "frame.png"
    spool.write_bytes(PNG_1X1)
    assert matches_declared_type("image/png", PNG_1X1)
    assert matches_declared_type("image/jpeg", JPEG_MIN)
    assert matches_declared_type("image/jpg", JPEG_MIN)
    assert matches_declared_type("image/webp", webp)
    assert matches_declared_type("image/heic", heif)
    assert matches_declared_type("image/heif", b"\x00\x00\x00\x18ftypheic")
    assert matches_declared_type("image/bmp", b"BM....")
    assert matches_declared_type("image/tiff", b"II*\x00")
    assert matches_declared_type("image/tif", b"MM\x00*")
    assert not matches_declared_type("image/png", b"not-a-png")
    assert not matches_declared_type("image/webp", b"RIFF\x00\x00\x00\x00XXXX")
    assert not matches_declared_type("application/octet-stream", PNG_1X1)
    assert header_bytes(
        ImageUpload(filename="f.png", content_type="image/png", spool_path=str(spool)),
    ).startswith(b"\x89PNG")
    assert header_bytes(ImageUpload(filename="f.png", content_type="image/png")) == b""
    assert header_bytes(
        ImageUpload(
            filename="f.png",
            content_type="image/png",
            header_prefix=PNG_1X1[:8],
        ),
    ).startswith(b"\x89PNG")


def test_production_requires_auth_and_tls() -> None:
    """ENVIRONMENT=production fails closed when auth or transport TLS is off."""
    with pytest.raises(RuntimeError, match="AUTH_REQUIRED"):
        validate_auth_settings(Settings(environment="production", auth_required=False))
    with pytest.raises(RuntimeError, match="HTTP_INSECURE"):
        validate_auth_settings(
            Settings(
                environment="prod",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=True,
                grpc_insecure=False,
            ),
        )
    with pytest.raises(RuntimeError, match="GRPC_INSECURE"):
        validate_auth_settings(
            Settings(
                environment="prod",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=False,
                grpc_insecure=True,
            ),
        )
    validate_auth_settings(
        Settings(
            environment="production",
            auth_required=True,
            api_keys="alpha:tenant-a",
            http_insecure=False,
            grpc_insecure=False,
            tls_cert_file=Path("/certs/server.crt"),
            tls_key_file=Path("/certs/server.key"),
            rate_limit_per_minute=60,
            tenant_max_upload_bytes=1024,
            session_max_upload_bytes=1024,
        ),
    )
    with pytest.raises(RuntimeError, match="RATE_LIMIT_PER_MINUTE"):
        validate_auth_settings(
            Settings(
                environment="production",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=False,
                grpc_insecure=False,
                tls_cert_file=Path("/certs/server.crt"),
                tls_key_file=Path("/certs/server.key"),
            ),
        )


def test_consumer_thresholds_are_not_looser_than_analog() -> None:
    """CI-022 overlay: analog keys exist; avg MI may be stricter than org 60."""
    import importlib.util
    from pathlib import Path

    path = Path("scripts/read_python_threshold.py")
    spec = importlib.util.spec_from_file_location("read_python_threshold", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = module.load_thresholds()
    assert values["max_cyclomatic_complexity"] == 8
    assert values["avg_maintainability_index"] == 70
    assert values["lint_exception_max_days"] == 14


@pytest.mark.asyncio
async def test_stream_image_skips_reload_when_row_passed(service: SessionService) -> None:
    """Download must not consume a second quota hit after get_image."""
    session = await service.create_session(sample_create())
    image = await service.add_image(
        session.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    calls = {"n": 0}
    original = service.get_image

    async def counted(
        session_id: object,
        image_id: object,
        principal: Principal | None = None,
    ) -> object:
        calls["n"] += 1
        return await original(session_id, image_id, principal)  # type: ignore[arg-type]

    service.get_image = counted  # type: ignore[method-assign]
    payload = b"".join(
        [chunk async for chunk in service.stream_image(session.id, image.id, image=image)],
    )
    assert payload == PNG_1X1
    assert calls["n"] == 0
    again = b"".join([chunk async for chunk in service.stream_image(session.id, image.id)])
    assert again == PNG_1X1
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_stream_image_rejects_mismatched_row(service: SessionService) -> None:
    """Passing another session's row must not stream that blob."""
    first = await service.create_session(sample_create())
    second = await service.create_session(sample_create())
    image = await service.add_image(
        second.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    with pytest.raises(ImageNotFoundError):
        async for _chunk in service.stream_image(first.id, image.id, image=image):
            pass


@pytest.mark.asyncio
async def test_rest_sdk_applies_token_to_shared_client(tmp_path: Path) -> None:
    """Bearer token is sent even when RestClient wraps an unauthenticated client."""
    settings = auth_settings(tmp_path, api_keys="alpha:tenant-a")
    service, engine = await make_service(settings)
    app = create_app(service)
    http = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    async with RestClient("http://test", token="alpha", client=http) as client:
        created = await client.create_session(sample_session_payload("token-run"))
        session_id = created["id"]
        uploaded = await client.upload_images_batch(
            session_id,
            [("a.png", PNG_1X1, "image/png"), ("b.png", PNG_1X1, "image/png")],
        )
        assert len(uploaded) == 2
    await engine.dispose()
