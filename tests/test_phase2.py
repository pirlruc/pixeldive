"""Phase 2 helpers: GC sweeper, Alembic, TLS, pagination, JSON logs."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from app.auth import authenticate, parse_api_keys
from app.config import Settings
from app.database import create_engine
from app.exceptions import InvalidIdError, UnauthenticatedError
from app.grpc_tls import build_grpc_server_credentials
from app.migrate import upgrade_head
from app.models import SessionUpdate
from app.observability import JsonLogFormatter, configure_logging
from app.pagination import decode_cursor, encode_cursor
from app.service import SessionService
from tests.conftest import JPEG_MIN, PNG_1X1, sample_create


@pytest.mark.asyncio
async def test_sweep_orphans_and_metadata_replace(service: SessionService, storage) -> None:
    """Sweeper deletes unreferenced blobs; replace metadata drops prior keys."""
    session = await service.create_session(sample_create())
    image = await service.add_image(
        session.id,
        __import__("app.models", fromlist=["ImageUpload"]).ImageUpload(
            filename="frame.png",
            content_type="image/png",
            payload=PNG_1X1,
        ),
    )
    orphan = await storage.save(JPEG_MIN, "image/jpeg")
    removed = await service.sweep_orphans(min_age_seconds=0)
    assert removed == 1
    assert not await storage.exists(orphan)
    assert await storage.exists(image.storage_path)
    replaced = await service.update_session(
        session.id,
        SessionUpdate(extra_metadata={"only": "this"}),
    )
    assert replaced.extra_metadata == {"only": "this"}


@pytest.mark.asyncio
async def test_alembic_creates_tables(tmp_path: Path) -> None:
    """alembic upgrade head creates the session tables."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}"
    await upgrade_head(url)
    engine = create_engine(Settings(database_url=url, auto_create_tables=False))
    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
        await connection.execute(text("SELECT 1"))
    await engine.dispose()
    assert "sessions" in tables
    assert "session_images" in tables


def test_parse_api_keys_and_authenticate() -> None:
    """JSON and pair forms parse; auth off returns None; bad tokens 401."""
    assert parse_api_keys("") == {}
    assert parse_api_keys("a:one,b:two") == {"a": "one", "b": "two"}
    assert parse_api_keys('{"tok": "tenant"}') == {"tok": "tenant"}
    assert parse_api_keys("solo") == {"solo": "solo"}
    settings = Settings(auth_required=False)
    assert authenticate(None, settings) is None
    required = Settings(auth_required=True, api_keys="secret:tenant")
    with pytest.raises(UnauthenticatedError):
        authenticate(None, required)
    principal = authenticate("Bearer secret", required)
    assert principal is not None
    assert principal.owner_id == "tenant"


def test_grpc_tls_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Insecure bind is explicit; TLS files are passed to grpc."""
    assert build_grpc_server_credentials(Settings(grpc_insecure=True)) is None
    with pytest.raises(RuntimeError):
        build_grpc_server_credentials(Settings(grpc_insecure=False))
    cert = tmp_path / "server.crt"
    key = tmp_path / "server.key"
    cert.write_bytes(b"cert")
    key.write_bytes(b"key")
    captured: dict[str, object] = {}

    def fake_creds(pairs, root_certificates=None, require_client_auth=False):
        captured["pairs"] = pairs
        captured["ca"] = root_certificates
        captured["mtls"] = require_client_auth
        return "creds"

    monkeypatch.setattr("app.grpc_tls.grpc.ssl_server_credentials", fake_creds)
    settings = Settings(
        grpc_insecure=False,
        grpc_tls_cert_file=cert,
        grpc_tls_key_file=key,
        grpc_tls_client_ca_file=cert,
    )
    assert build_grpc_server_credentials(settings) == "creds"
    assert captured["mtls"] is True
    shared = Settings(grpc_insecure=False, tls_cert_file=cert, tls_key_file=key)
    assert build_grpc_server_credentials(shared) == "creds"


def test_cursor_and_json_logs() -> None:
    """Cursors round-trip; JSON formatter includes request_id."""
    import logging
    import uuid
    from datetime import UTC, datetime

    stamp = datetime.now(UTC)
    item_id = uuid.uuid4()
    cursor = encode_cursor(stamp, item_id)
    decoded_stamp, decoded_id = decode_cursor(cursor)
    assert decoded_id == item_id
    assert decoded_stamp == stamp
    with pytest.raises(InvalidIdError):
        decode_cursor("not-a-cursor")
    configure_logging(json_logs=True)
    record = logging.LogRecord("pixeldive", logging.INFO, __file__, 1, "hello", None, None)
    record.request_id = "abc"
    line = JsonLogFormatter().format(record)
    assert '"request_id": "abc"' in line
    configure_logging(json_logs=False)


@pytest.mark.asyncio
async def test_ready_503_when_db_down(service: SessionService) -> None:
    """/ready returns 503 when ping_db fails."""
    from httpx import ASGITransport, AsyncClient

    from app.api import create_app

    async def boom() -> None:
        raise RuntimeError("db down")

    service.ping_db = boom  # type: ignore[method-assign]
    app = create_app(service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/ready")
    assert response.status_code == 503


def test_main_rejects_auth_without_keys() -> None:
    """AUTH_REQUIRED with empty API_KEYS fails at startup."""
    from app.runtime import validate_auth_settings

    with pytest.raises(RuntimeError, match="API_KEYS"):
        validate_auth_settings(Settings(auth_required=True, api_keys=""))


def test_main_rejects_production_without_auth() -> None:
    """Production profile cannot boot with AUTH_REQUIRED off."""
    from app.runtime import validate_auth_settings

    with pytest.raises(RuntimeError, match="AUTH_REQUIRED"):
        validate_auth_settings(Settings(environment="production"))
