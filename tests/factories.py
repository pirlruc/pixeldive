"""Shared SessionService construction for isolated auth/quota/TLS tests."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.blobs.storage import LocalFilesystemStorage
from app.config import Settings
from app.database import create_engine, init_db, session_factory
from app.sessions.service import SessionService


def isolated_settings(tmp_path: Path, **overrides: object) -> Settings:
    """SQLite + local disk settings, with optional auth/quota/TLS overrides."""
    values: dict[str, object] = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'isolated.db'}",
        "storage_backend": "local",
        "storage_root": tmp_path / "images",
        "log_json": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def auth_settings(tmp_path: Path, **overrides: object) -> Settings:
    """Authenticated isolated settings with two demo tenants."""
    values: dict[str, object] = {
        "auth_required": True,
        "api_keys": "alpha:tenant-a,beta:tenant-b",
    }
    values.update(overrides)
    return isolated_settings(tmp_path, **values)


async def make_service(settings: Settings) -> tuple[SessionService, AsyncEngine]:
    """Create tables and a SessionService bound to local storage."""
    engine = create_engine(settings)
    await init_db(engine)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    service = SessionService(
        session_factory(engine),
        LocalFilesystemStorage(settings.storage_root),
        settings,
    )
    return service, engine
