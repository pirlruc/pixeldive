"""Phase 2 schema: sessions and session_images.

Revision ID: 0001_phase2
Revises:
Create Date: 2026-09-19

The operations are explicit. ``SQLModel.metadata.create_all`` is not used,
so a later model does not appear in this revision. Databases that already
have ``sessions`` from an older ``create_all`` only gain ``owner_id`` when
that column is missing.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.device_models import CameraCapabilities, PhoneCapabilities, PhoneInfo
from app.json_columns import PydanticJSON

revision = "0001_phase2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the session tables, or add owner_id on a Phase 1 database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sessions" not in tables:
        _create_sessions()
        _create_session_images()
        return
    columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "owner_id" not in columns:
        op.add_column("sessions", sa.Column("owner_id", sa.String(length=128), nullable=True))
        op.create_index("ix_sessions_owner_id", "sessions", ["owner_id"])


def downgrade() -> None:
    """Drop session tables."""
    op.drop_table("session_images")
    op.drop_table("sessions")


def _create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phone_info", PydanticJSON(PhoneInfo), nullable=False),
        sa.Column("phone_capabilities", PydanticJSON(PhoneCapabilities), nullable=False),
        sa.Column("camera_capabilities", PydanticJSON(CameraCapabilities), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "status IN ('CREATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED')",
            name="ck_session_status",
        ),
    )
    op.create_index("ix_sessions_status", "sessions", ["status"])
    op.create_index("ix_sessions_owner_id", "sessions", ["owner_id"])


def _create_session_images() -> None:
    op.create_table(
        "session_images",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_session_images_session_id", "session_images", ["session_id"])
    op.create_index("ix_session_images_storage_path", "session_images", ["storage_path"])
