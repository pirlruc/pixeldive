"""Upload validation helpers for SessionService."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.content_types import ALLOWED_CONTENT_TYPES
from app.exceptions import EmptyImageError, ImageTooLargeError, UnsupportedContentTypeError
from app.filenames import sanitize_filename
from app.magic import header_bytes, matches_declared_type
from app.models import ImageUpload


def normalize_content_type(raw: str | None) -> str:
    """Return a lowercase type without parameters."""
    return (raw or "").split(";")[0].strip().lower()


def upload_size(upload: ImageUpload) -> int:
    """Return the spool length, or the in-memory payload length when there is no spool."""
    if upload.spool_path:
        return Path(upload.spool_path).stat().st_size
    return len(upload.payload)


def validate_upload(upload: ImageUpload, settings: Settings) -> None:
    """Reject empty, oversized, or non-image payloads."""
    content_type = normalize_content_type(upload.content_type)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedContentTypeError(f"unsupported content type: {upload.content_type}")
    size = upload_size(upload)
    if size <= 0:
        raise EmptyImageError("image payload is empty")
    if size > settings.max_image_bytes:
        raise ImageTooLargeError(
            f"image exceeds max_image_bytes={settings.max_image_bytes}",
        )
    if not matches_declared_type(content_type, header_bytes(upload)):
        raise UnsupportedContentTypeError(
            f"payload does not match content type: {upload.content_type}",
        )
    upload.content_type = content_type
    upload.size_bytes = size
    upload.filename = sanitize_filename(upload.filename)
