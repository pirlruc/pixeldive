"""Runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings for the dual REST/gRPC server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    max_image_bytes: int = 32 * 1024 * 1024
    max_batch_images: int = 100
    download_chunk_bytes: int = 64 * 1024

    @field_validator("storage_backend")
    @classmethod
    def _backend_name(cls, value: str) -> str:
        """Reject unknown storage backends early."""
        allowed = {"local", "s3"}
        if value not in allowed:
            msg = f"storage_backend must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
