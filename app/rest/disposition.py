"""RFC 5987 Content-Disposition values for image downloads."""

from urllib.parse import quote

from app.blobs.filenames import sanitize_filename


def attachment_disposition(filename: str) -> str:
    """Return a header that cannot inject extra fields via the filename."""
    safe = sanitize_filename(filename)
    encoded = quote(safe, safe="")
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{encoded}"
