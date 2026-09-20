"""First-byte sniffing so uploads cannot hide behind a forged Content-Type."""

from pathlib import Path

from app.models import ImageUpload

_PREFIXES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/jpg": (b"\xff\xd8\xff",),
    "image/bmp": (b"BM",),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
    "image/tif": (b"II*\x00", b"MM\x00*"),
}
_HEIF = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"}


def header_bytes(upload: ImageUpload, size: int = 16) -> bytes:
    """Return the first ``size`` bytes from memory or a spool file."""
    if upload.payload:
        return upload.payload[:size]
    if upload.spool_path:
        with Path(upload.spool_path).open("rb") as handle:
            return handle.read(size)
    return b""


def _webp(header: bytes) -> bool:
    """True when ``header`` is a RIFF/WEBP box."""
    return header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def _heif(header: bytes) -> bool:
    """True when ``header`` is an ISO-BMFF ftyp with a HEIF brand."""
    return header[4:8] == b"ftyp" and header[8:12] in _HEIF


def matches_declared_type(content_type: str, header: bytes) -> bool:
    """True when ``header`` matches the declared image content type."""
    if content_type == "image/webp":
        return _webp(header)
    if content_type in {"image/heic", "image/heif"}:
        return _heif(header)
    prefixes = _PREFIXES.get(content_type, ())
    return any(header.startswith(item) for item in prefixes)
