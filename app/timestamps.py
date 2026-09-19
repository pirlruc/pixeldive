"""UTC clocks and session lifecycle status values."""

from datetime import UTC, datetime
from enum import StrEnum


def utcnow() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class SessionStatus(StrEnum):
    """Lifecycle values persisted on ``sessions.status``."""

    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
