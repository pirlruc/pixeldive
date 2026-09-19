"""SHA-256 object keys for content-addressed image blobs."""

import hashlib

from app.content_types import ALLOWED_CONTENT_TYPES


def sha256_hex(payload: bytes) -> str:
    """Return the SHA-256 hex digest of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


def object_key(digest: str, content_type: str) -> str:
    """Build a two-level hash prefix path with a content-type extension."""
    extension = ALLOWED_CONTENT_TYPES.get(content_type, ".bin")
    return f"{digest[:2]}/{digest[2:4]}/{digest}{extension}"
