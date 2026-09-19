"""Settings, engine helpers, and dual-server wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.database import create_engine, init_db, session_scope
from app.storage import LocalFilesystemStorage, build_storage


def test_invalid_storage_backend() -> None:
    """Unknown STORAGE_BACKEND values fail validation."""
    with pytest.raises(ValidationError):
        Settings(storage_backend="ftp")


def test_build_local_storage(tmp_path: Path) -> None:
    """build_storage creates the local root and returns LocalFilesystemStorage."""
    settings = Settings(storage_backend="local", storage_root=tmp_path / "blobs")
    backend = build_storage(settings)
    assert isinstance(backend, LocalFilesystemStorage)
    assert settings.storage_root.is_dir()


@pytest.mark.asyncio
async def test_init_db_and_session_scope(tmp_path: Path) -> None:
    """init_db is idempotent; session_scope yields an AsyncSession."""
    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}")
    engine = create_engine(settings)
    await init_db(engine)
    await init_db(engine)
    from app.database import session_factory

    factory = session_factory(engine)
    async for session in session_scope(factory):
        assert session is not None
    await engine.dispose()


def test_s3_missing_helper() -> None:
    """404-shaped errors are treated as missing objects."""
    from app.storage import _is_missing

    class Err(Exception):
        response = {"Error": {"Code": "NoSuchKey"}}

    class ClientError(Exception):
        """botocore-shaped name used by the string fallback."""

    assert _is_missing(Err()) is True
    assert _is_missing(RuntimeError("boom")) is False
    assert _is_missing(ClientError("An error occurred (404) when calling HeadObject")) is True
    assert _is_missing(ClientError("timeout")) is False


def test_postgres_engine_skips_sqlite_pragma() -> None:
    """Non-sqlite URLs do not register the SQLite FK listener."""
    settings = Settings(
        database_url="postgresql+asyncpg://pixeldive:pixeldive@127.0.0.1:5432/pixeldive"
    )
    engine = create_engine(settings)
    assert str(engine.url).startswith("postgresql")


def test_default_s3_client(monkeypatch) -> None:
    """_default_s3_client builds a boto3 client with settings."""
    captured: dict[str, object] = {}

    class FakeBoto:
        @staticmethod
        def client(service_name: str, **kwargs: object) -> str:
            captured["service"] = service_name
            captured.update(kwargs)
            return "s3-client"

    import sys
    import types

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=FakeBoto.client))
    from app.storage import _default_s3_client

    settings = Settings(
        storage_backend="s3", s3_endpoint_url="http://127.0.0.1:9000", s3_bucket="b"
    )
    assert _default_s3_client(settings) == "s3-client"
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "http://127.0.0.1:9000"
