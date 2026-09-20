"""Database and blob-store settings mixed into Settings."""

from pathlib import Path

from pydantic import Field


class StorageSettingsMixin:
    """SQL, local/S3 storage, and GC grace periods."""

    database_url: str = Field(
        default="postgresql+asyncpg://pixeldive:pixeldive@127.0.0.1:5432/pixeldive",
        description="SQLAlchemy async URL (asyncpg in production, aiosqlite in tests).",
    )
    storage_backend: str = Field(default="local", description="local or s3")
    storage_root: Path = Field(default=Path("/data/images"))
    s3_endpoint_url: str | None = None
    s3_bucket: str = "pixeldive"
    s3_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    gc_min_age_seconds: float = 0.0
    orphan_min_age_seconds: float = 60.0
    s3_multipart_bytes: int = 8 * 1024 * 1024
    auto_create_tables: bool = True
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True
