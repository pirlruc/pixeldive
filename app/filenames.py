"""Sanitize client-supplied filenames for metadata and download headers."""

from pathlib import Path

_MAX_LEN = 255


def sanitize_filename(name: str | None) -> str:
    """Return a path-free filename safe to put in Content-Disposition."""
    raw = Path(name or "upload.bin").name
    cleaned = "".join(ch for ch in raw if ch not in {'"', "\\", "\r", "\n"} and ord(ch) >= 32)
    cleaned = cleaned.strip(" .")[:_MAX_LEN]
    return cleaned or "upload.bin"
