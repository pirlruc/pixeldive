"""Opaque list-cursor encoding (timestamp + UUID)."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime

from app.exceptions import InvalidIdError


def encode_cursor(stamp: datetime, item_id: uuid.UUID) -> str:
    """Encode ``(timestamp, id)`` as a URL-safe cursor."""
    raw = f"{stamp.isoformat()}|{item_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a cursor produced by :func:`encode_cursor`."""
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        stamp_s, id_s = raw.split("|", 1)
        return datetime.fromisoformat(stamp_s), uuid.UUID(id_s)
    except (ValueError, OSError) as exc:
        raise InvalidIdError("invalid cursor") from exc
