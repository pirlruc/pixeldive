"""Public request/response schemas for sessions and images."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, model_validator
from pydantic import Field as PydField
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from app.device_models import CameraCapabilities, PhoneCapabilities, PhoneInfo
from app.sessions.metadata import promote_metadata
from app.timestamps import SessionStatus


class SessionCreate(SQLModel):
    """POST /sessions payload."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)  # type: ignore[assignment]

    session_name: str = SQLField(min_length=1, max_length=255)
    phone_info: PhoneInfo
    phone_capabilities: PhoneCapabilities
    camera_capabilities: CameraCapabilities
    extra_metadata: dict[str, Any] = PydField(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "extra_metadata"),
        serialization_alias="metadata",
    )

    @model_validator(mode="before")
    @classmethod
    def _metadata_key(cls, data: Any) -> Any:
        """Accept ``metadata`` as the public JSON name."""
        return promote_metadata(data)


class SessionUpdate(SQLModel):
    """PUT /sessions/{id} payload — all fields optional."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)  # type: ignore[assignment]

    session_name: str | None = SQLField(default=None, min_length=1, max_length=255)
    status: SessionStatus | None = None
    extra_metadata: dict[str, Any] | None = PydField(
        default=None,
        validation_alias=AliasChoices("metadata", "extra_metadata"),
        serialization_alias="metadata",
    )
    merge_metadata: bool = False

    @model_validator(mode="before")
    @classmethod
    def _metadata_key(cls, data: Any) -> Any:
        """Accept ``metadata`` as the public JSON name."""
        return promote_metadata(data)


class SessionRead(SQLModel):
    """Public session representation."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, serialize_by_alias=True)  # type: ignore[assignment]

    id: uuid.UUID
    session_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    phone_info: PhoneInfo
    phone_capabilities: PhoneCapabilities
    camera_capabilities: CameraCapabilities
    extra_metadata: dict[str, Any] = PydField(
        default_factory=dict,
        serialization_alias="metadata",
    )


class SessionPage(SQLModel):
    """Paginated session list (API-002)."""

    model_config = ConfigDict(from_attributes=True)  # type: ignore[assignment]

    items: list[SessionRead]
    next_cursor: str | None = None


class SessionImageRead(SQLModel):
    """Public image metadata (no raw bytes, no storage_path)."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, serialize_by_alias=True)  # type: ignore[assignment]

    id: uuid.UUID
    session_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    extra_metadata: dict[str, Any] = PydField(
        default_factory=dict,
        serialization_alias="metadata",
    )


class ImagePage(SQLModel):
    """Paginated image list (PERF-001)."""

    model_config = ConfigDict(from_attributes=True)  # type: ignore[assignment]

    items: list[SessionImageRead]
    next_cursor: str | None = None


class ImageUpload(SQLModel):
    """Upload accepted by SessionService (bytes and/or a hashed spool)."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)  # type: ignore[assignment]

    filename: str
    content_type: str
    payload: bytes = b""
    extra_metadata: dict[str, Any] = PydField(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "extra_metadata"),
        serialization_alias="metadata",
    )
    spool_path: str | None = None
    digest_hex: str | None = None
    size_bytes: int = 0
    header_prefix: bytes = b""

    @model_validator(mode="before")
    @classmethod
    def _metadata_key(cls, data: Any) -> Any:
        """Accept ``metadata`` as the public JSON name."""
        return promote_metadata(data)
