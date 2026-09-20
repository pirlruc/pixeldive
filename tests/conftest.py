"""Shared pytest fixtures: SQLite engine, local storage, SessionService, ASGI client."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api import create_app
from app.config import Settings
from app.database import create_engine, init_db, session_factory
from app.models import CameraCapabilities, PhoneCapabilities, PhoneInfo, SessionCreate
from app.service import SessionService
from app.storage import LocalFilesystemStorage

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

JPEG_MIN = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda00080001000100003f00fbd5ffd9"
)


def sample_phone_info() -> PhoneInfo:
    """Return a Pixel-like Build.* payload."""
    return PhoneInfo(
        manufacturer="Google",
        model="Pixel 8",
        brand="google",
        device="shiba",
        board="shiba",
        android_version="14",
        sdk_int=34,
    )


def sample_phone_caps() -> PhoneCapabilities:
    """Return ActivityManager/DisplayMetrics-style capabilities."""
    return PhoneCapabilities(
        total_ram_mb=8192,
        available_ram_mb=4096,
        cpu_abi="arm64-v8a",
        cpu_cores=8,
        screen_width_px=1080,
        screen_height_px=2400,
        screen_density_dpi=420,
        is_low_ram_device=False,
    )


def sample_cameras() -> CameraCapabilities:
    """Return a back+front Camera2 enumeration."""
    return CameraCapabilities(
        camera_count=2,
        cameras=[
            {
                "camera_id": "0",
                "lens_facing": "BACK",
                "hardware_level": "LEVEL_3",
                "sensor_orientation": 90,
                "max_resolution": "4080x3072",
                "has_flash": True,
                "has_optical_stabilization": True,
                "supported_capabilities": ["BACKWARD_COMPATIBLE", "RAW"],
            },
            {
                "camera_id": "1",
                "lens_facing": "FRONT",
                "hardware_level": "LIMITED",
                "sensor_orientation": 270,
                "max_resolution": "3264x2448",
                "has_flash": False,
                "has_optical_stabilization": False,
                "supported_capabilities": ["BACKWARD_COMPATIBLE"],
            },
        ],
    )


def sample_create(**overrides: object) -> SessionCreate:
    """Build a valid SessionCreate payload."""
    payload = {
        "session_name": "capture-run",
        "phone_info": sample_phone_info(),
        "phone_capabilities": sample_phone_caps(),
        "camera_capabilities": sample_cameras(),
        "metadata": {"capture_mode": "burst"},
    }
    payload.update(overrides)
    return SessionCreate.model_validate(payload)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Test settings using SQLite by default, or Postgres when CI sets the URL."""
    database_url = os.environ.get("PIXELDIVE_TEST_DATABASE_URL")
    if database_url:
        return Settings(
            database_url=database_url,
            storage_backend="local",
            storage_root=tmp_path / "images",
            max_image_bytes=1024 * 1024,
            download_chunk_bytes=16,
            auto_create_tables=False,
            log_json=False,
        )
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        storage_backend="local",
        storage_root=tmp_path / "images",
        max_image_bytes=1024 * 1024,
        download_chunk_bytes=16,
    )


async def _reset_postgres(engine: AsyncEngine) -> None:
    """Delete session rows so Postgres tests stay isolated (DATA-003)."""
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM session_images"))
        await connection.execute(text("DELETE FROM sessions"))


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """Create tables (SQLite) or truncate (Postgres) and dispose afterward."""
    engine = create_engine(settings)
    if settings.database_url.startswith("sqlite"):
        await init_db(engine)
    else:
        await _reset_postgres(engine)
    try:
        yield engine
    finally:
        if not settings.database_url.startswith("sqlite"):
            await _reset_postgres(engine)
        await engine.dispose()


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Async session factory bound to the test engine."""
    return session_factory(engine)


@pytest.fixture
def storage(settings: Settings) -> LocalFilesystemStorage:
    """Local filesystem backend under the test tmp path."""
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return LocalFilesystemStorage(settings.storage_root)


@pytest.fixture
def service(
    factory: async_sessionmaker[AsyncSession],
    storage: LocalFilesystemStorage,
    settings: Settings,
) -> SessionService:
    """SessionService wired to SQLite + local disk."""
    return SessionService(factory, storage, settings)


@pytest_asyncio.fixture
async def client(service: SessionService) -> AsyncIterator[AsyncClient]:
    """HTTPX ASGI client against the FastAPI app."""
    app = create_app(service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
