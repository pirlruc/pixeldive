"""Alembic upgrade helper used when AUTO_CREATE_TABLES is false (DATA-002)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str) -> Config:
    """Build an Alembic Config pointed at this repo and ``database_url``."""
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def upgrade_head_sync(database_url: str) -> None:
    """Run ``alembic upgrade head`` against ``database_url``."""
    command.upgrade(alembic_config(database_url), "head")


async def upgrade_head(database_url: str) -> None:
    """Run migrations on a worker thread so the event loop stays free."""
    await asyncio.to_thread(upgrade_head_sync, database_url)
