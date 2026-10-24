"""SQLModel table for shared tenant and session quota counters (SEC-004)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, String, Text, text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class TenantQuotaRow(SQLModel, table=True):
    """One quota scope: a tenant rate/byte row or a session byte row."""

    __tablename__ = "tenant_quota"

    scope: str = SQLField(sa_column=Column(String(192), primary_key=True))
    bytes_used: int = SQLField(
        sa_column=Column(BigInteger, nullable=False, server_default=text("0")),
    )
    hits: str = SQLField(
        sa_column=Column(Text, nullable=False, server_default=text("'[]'")),
    )
