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
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict) and str(error.get("Code", "")) in {
            "404",
            "NotFound",
            "NoSuchKey",
        }:
            return True
        meta = response.get("ResponseMetadata")
        if isinstance(meta, dict) and meta.get("HTTPStatusCode") == 404:
            return True
    return type(exc).__name__ in {"NoSuchKey", "NotFound"}


def missing_or_raise(exc: BaseException) -> None:
    """No-op for missing-key errors; re-raise anything else."""
    if is_missing(exc):
        return
    raise exc


def age_from_head(response: object) -> float:
    """Compute object age from a HEAD response; missing LastModified is 0."""
    last = response.get("LastModified") if isinstance(response, dict) else None
    return max(0.0, time.time() - mtime(last)) if last is not None else 0.0
