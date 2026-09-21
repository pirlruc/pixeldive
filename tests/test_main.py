"""Entrypoint wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

import main as main_mod
from app.config import Settings, get_settings
from app.exceptions import EmptyImageError, InvalidStatusError
from app.metadata import parse_metadata_json
from app.models import ImageUpload, PhoneInfo, PydanticJSON, SessionUpdate
from app.service import SessionService
from app.storage import build_storage
from tests.conftest import sample_create, sample_phone_info


def test_main_runs_event_loop(monkeypatch) -> None:
    """main() drives asyncio.run(run())."""

    async def fake_run(settings=None):
        del settings
        return None

    monkeypatch.setattr(main_mod, "run", fake_run)
    main_mod.main()


def _patch_dual_servers(monkeypatch, runtime, flags: dict[str, bool]) -> None:
    """Replace gRPC start and HTTP bind with in-memory fakes."""

    class FakeGrpc:
        async def wait_for_termination(self) -> None:
            flags["grpc"] = True

        async def stop(self, grace: object = None) -> None:
            del grace
            flags["stopped"] = True

    class FakeHttp:
        async def serve(self) -> None:
            flags["http"] = True

    async def fake_start(*args, **kwargs):
        del args, kwargs
        return FakeGrpc(), 9

    monkeypatch.setattr(runtime, "start_grpc_server", fake_start)
    monkeypatch.setattr(runtime, "build_http_server", lambda app, settings: FakeHttp())


@pytest.mark.asyncio
async def test_run_starts_http_and_grpc(monkeypatch, tmp_path: Path) -> None:
    """run() gathers HTTP serve and gRPC wait, then stops the gRPC server."""
    import app.runtime as runtime

    flags: dict[str, bool] = {}
    _patch_dual_servers(monkeypatch, runtime, flags)
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'run.db'}",
        storage_root=tmp_path / "img",
        storage_backend="local",
    )
    await runtime.run(settings)
    assert flags["http"] is True
    assert flags["grpc"] is True
    assert flags["stopped"] is True


@pytest.mark.asyncio
async def test_run_uses_alembic_when_create_all_disabled(monkeypatch, tmp_path: Path) -> None:
    """Production path runs Alembic instead of create_all."""
    import app.runtime as runtime

    flags: dict[str, bool] = {}
    _patch_dual_servers(monkeypatch, runtime, flags)

    async def fake_upgrade(url: str) -> None:
        flags["migrated"] = True
        from app.database import create_engine, init_db

        engine = create_engine(Settings(database_url=url))
        await init_db(engine)
        await engine.dispose()

    monkeypatch.setattr(runtime, "upgrade_head", fake_upgrade)
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'run.db'}",
        storage_root=tmp_path / "img",
        storage_backend="local",
        auto_create_tables=False,
        log_json=False,
    )
    await runtime.run(settings)
    assert flags["migrated"] is True
    assert flags["http"] is True


def test_get_settings_cache() -> None:
    """get_settings is lru-cached."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
    get_settings.cache_clear()


def test_pydantic_json_round_trip() -> None:
    """PydanticJSON dumps and rehydrates nested models."""
    codec = PydanticJSON(PhoneInfo)
    dumped = codec.process_bind_param(sample_phone_info(), None)
    assert dumped["model"] == "Pixel 8"
    loaded = codec.process_result_value(dumped, None)
    assert loaded.sdk_int == 34
    assert codec.process_bind_param(None, None) is None
    assert codec.process_result_value(None, None) is None
    again = codec.process_bind_param(dumped, None)
    assert again["manufacturer"] == "Google"


@pytest.mark.asyncio
async def test_empty_image_and_invalid_status(service: SessionService) -> None:
    """Empty payloads and constructed invalid statuses raise service errors."""
    session = await service.create_session(sample_create())
    with pytest.raises(EmptyImageError):
        await service.add_image(
            session.id,
            ImageUpload(filename="x.png", content_type="image/png", payload=b""),
        )
    with pytest.raises(InvalidStatusError):
        await service.update_session(session.id, SessionUpdate.model_construct(status="NOPE"))


def test_parse_metadata_invalid_json() -> None:
    """Non-JSON metadata strings are InvalidMetadataError."""
    from app.exceptions import InvalidMetadataError

    with pytest.raises(InvalidMetadataError):
        parse_metadata_json("{")


def test_build_s3_storage(tmp_path: Path) -> None:
    """STORAGE_BACKEND=s3 uses the injected client factory."""
    settings = Settings(storage_backend="s3", s3_bucket="pixeldive", storage_root=tmp_path)
    from tests.test_storage import FakeS3

    backend = build_storage(settings, s3_factory=lambda _s: FakeS3())
    assert backend.__class__.__name__ == "S3CompatibleStorage"
