"""SQLModel tables for sessions and images.

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

from pydantic import ConfigDict
from sqlalchemy import JSON, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
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
from app.schemas import (
    ImagePage,
    ImageUpload,
    SessionCreate,
    SessionImageRead,
    SessionPage,
    SessionRead,
    SessionUpdate,
)
from app.timestamps import SessionStatus, utcnow

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "CameraCapabilities",
    "CameraInfo",
    "ImagePage",
    "ImageUpload",
    "PhoneCapabilities",
    "PhoneInfo",
    "PydanticJSON",
    "Session",
    "SessionCreate",
    "SessionImage",
    "SessionImageRead",
    "SessionPage",
    "SessionRead",
    "SessionStatus",
    "SessionUpdate",
    "utcnow",
]


class Session(SQLModel, table=True):
    """Persisted capture session and device specification."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED')",
            name="ck_session_status",
        ),
    )
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
    owner_id: str | None = SQLField(default=None, max_length=128, index=True)
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
