"""Runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.settings_runtime import RuntimeSettingsMixin
from app.settings_storage import StorageSettingsMixin


class Settings(StorageSettingsMixin, RuntimeSettingsMixin, BaseSettings):
    """Process-wide settings for the dual REST/gRPC server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("storage_backend")
    @classmethod
    def _backend_name(cls, value: str) -> str:
        """Reject unknown storage backends early."""
        allowed = {"local", "s3"}
        if value not in allowed:
            msg = f"storage_backend must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value

    def api_key_map(self) -> dict[str, str]:
        """Parse ``api_keys`` into token → owner_id."""
        from app.auth import parse_api_keys

        return parse_api_keys(self.api_keys)

    def spool_dir(self) -> Path:
        """Directory for hashed upload spools under the storage root."""
        path = self.storage_root / ".incoming"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
