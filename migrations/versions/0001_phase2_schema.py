"""Phase 2 schema: sessions, session_images, owner_id, status check.

Revision ID: 0001_phase2
Revises:
Create Date: 2026-09-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlmodel import SQLModel

from app.models import Session, SessionImage  # noqa: F401

revision = "0001_phase2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables or add owner_id onto a Phase 1 database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sessions" not in tables:
        SQLModel.metadata.create_all(bind)
        return
    columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "owner_id" not in columns:
        op.add_column("sessions", sa.Column("owner_id", sa.String(length=128), nullable=True))
        op.create_index("ix_sessions_owner_id", "sessions", ["owner_id"])


def downgrade() -> None:
    """Drop session tables."""
    op.drop_table("session_images")
    op.drop_table("sessions")
