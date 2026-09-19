"""SQLModel tables and Pydantic schemas for sessions and images.

Nested JSON payloads use the same keys Android clients already collect:

* ``phone_info`` — ``android.os.Build``
* ``phone_capabilities`` — ``ActivityManager``, ``Runtime``, ``DisplayMetrics``
* ``camera_capabilities`` — Camera2 ``CameraCharacteristics``

SQLAlchemy reserves ``metadata`` on declarative classes, so the JSON bag is
stored as column ``metadata`` and exposed as ``extra_metadata`` with alias
``metadata`` (DATA-001).
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import AliasChoices, ConfigDict, model_validator
from pydantic import Field as PydField
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.types import Uuid
from sqlmodel import Field as SQLField
from sqlmodel import Relationship, SQLModel

from app.content_types import ALLOWED_CONTENT_TYPES
from app.device_models import (
    CameraCapabilities,
    CameraInfo,
    PhoneCapabilities,
    PhoneInfo,
    PydanticJSON,
)
from app.metadata import promote_metadata
from app.timestamps import SessionStatus, utcnow

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "CameraCapabilities",
    "CameraInfo",
    "ImageUpload",
    "PhoneCapabilities",
    "PhoneInfo",
    "PydanticJSON",
    "Session",
    "SessionCreate",
    "SessionImage",
    "SessionImageRead",
    "SessionRead",
    "SessionStatus",
    "SessionUpdate",
    "utcnow",
]


class Session(SQLModel, table=True):
    """Persisted capture session and device specification."""

    __tablename__ = "sessions"
    model_config = ConfigDict(populate_by_name=True)  # type: ignore[assignment]

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    session_name: str = SQLField(min_length=1, max_length=255)
    status: str = SQLField(default=SessionStatus.CREATED.value, index=True)
    created_at: datetime = SQLField(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = SQLField(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    phone_info: PhoneInfo = SQLField(sa_column=Column(PydanticJSON(PhoneInfo), nullable=False))
    phone_capabilities: PhoneCapabilities = SQLField(
        sa_column=Column(PydanticJSON(PhoneCapabilities), nullable=False),
    )
    camera_capabilities: CameraCapabilities = SQLField(
        sa_column=Column(PydanticJSON(CameraCapabilities), nullable=False),
    )
    extra_metadata: dict[str, Any] = SQLField(
        default_factory=dict,
        alias="metadata",
        sa_column=Column("metadata", JSON, nullable=False, default=dict),
    )
    images: list["SessionImage"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )


class SessionImage(SQLModel, table=True):
    """One uploaded image belonging to a session."""

    __tablename__ = "session_images"
    model_config = ConfigDict(populate_by_name=True)  # type: ignore[assignment]

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = SQLField(
        sa_column=Column(
            Uuid,
            ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    filename: str = SQLField(sa_column=Column(String(512), nullable=False))
    content_type: str = SQLField(sa_column=Column(String(128), nullable=False))
    size_bytes: int = SQLField(sa_column=Column(Integer, nullable=False))
    storage_path: str = SQLField(sa_column=Column(Text, nullable=False, index=True))
    uploaded_at: datetime = SQLField(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    extra_metadata: dict[str, Any] = SQLField(
        default_factory=dict,
        alias="metadata",
        sa_column=Column("metadata", JSON, nullable=False, default=dict),
    )
    session: Optional["Session"] = Relationship(back_populates="images")


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


class SessionImageRead(SQLModel):
    """Public image metadata (no raw bytes)."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, serialize_by_alias=True)  # type: ignore[assignment]

    id: uuid.UUID
    session_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    uploaded_at: datetime
    extra_metadata: dict[str, Any] = PydField(
        default_factory=dict,
        serialization_alias="metadata",
    )


class ImageUpload(SQLModel):
    """In-memory upload accepted by SessionService."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)  # type: ignore[assignment]

    filename: str
    content_type: str
    payload: bytes
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
