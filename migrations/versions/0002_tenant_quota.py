"""Shared tenant quota counters.

Revision ID: 0002_tenant_quota
Revises: 0001_phase2
Create Date: 2026-10-23

Fresh databases gain only ``tenant_quota`` here. A database that already has
the table from ``create_all`` is left alone.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_tenant_quota"
down_revision = "0001_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ``tenant_quota`` unless a previous create_all already did."""
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "tenant_quota" in tables:
        return
    op.create_table(
        "tenant_quota",
        sa.Column("scope", sa.String(length=192), primary_key=True, nullable=False),
        sa.Column(
            "bytes_used",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "hits",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    """Drop ``tenant_quota`` when it is present."""
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "tenant_quota" not in tables:
        return
    op.drop_table("tenant_quota")
