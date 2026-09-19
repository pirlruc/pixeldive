"""Status and metadata patch helpers for SessionService."""

from __future__ import annotations

from typing import Any

from app.exceptions import InvalidStatusError
from app.models import SessionStatus


def status_value(status: SessionStatus | str) -> str:
    """Normalize and validate a status string."""
    value = status.value if isinstance(status, SessionStatus) else str(status)
    allowed = {item.value for item in SessionStatus}
    if value not in allowed:
        raise InvalidStatusError(f"invalid status: {value}")
    return value


def apply_metadata(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    merge: bool,
) -> dict[str, Any]:
    """Replace or shallow-merge the JSON metadata bag."""
    if not merge:
        return incoming
    merged = dict(existing)
    merged.update(incoming)
    return merged
