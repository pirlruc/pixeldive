"""List/mtime helpers for the S3-compatible blob backend."""

from __future__ import annotations

import time
from datetime import datetime


def contents(response: dict[str, object]) -> list[dict[str, object]]:
    """Extract the Contents list from a list_objects_v2 response."""
    raw = response.get("Contents") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def mtime(value: object) -> float:
    """Convert a LastModified datetime (or unix timestamp) to epoch seconds."""
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def is_missing(exc: BaseException) -> bool:
    """Return True for S3 404 / NotFound client errors."""
    response = getattr(exc, "response", None) if hasattr(exc, "response") else None
    status = None
    if isinstance(response, dict):
        status = response.get("Error", {}).get("Code")
    if status in {"404", "NotFound", "NoSuchKey"}:
        return True
    name = type(exc).__name__
    return name in {"NoSuchKey", "ClientError"} and "404" in str(exc)


def age_from_head(response: object) -> float:
    """Compute object age from a HEAD response; missing LastModified is 0."""
    last = response.get("LastModified") if isinstance(response, dict) else None
    return max(0.0, time.time() - mtime(last)) if last is not None else 0.0
