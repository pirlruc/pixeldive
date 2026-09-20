"""First-byte sniffing so uploads cannot hide behind a forged Content-Type."""

from pathlib import Path

from app.models import ImageUpload

PREFIXES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/jpg": (b"\xff\xd8\xff",),
    "image/bmp": (b"BM",),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
    "image/tif": (b"II*\x00", b"MM\x00*"),
}

HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"}


def header_bytes(upload: ImageUpload, size: int = 16) -> bytes:
    """Return the first ``size`` bytes from memory or a spool file."""
    if upload.payload:
        return upload.payload[:size]
    if upload.spool_path:
        with Path(upload.spool_path).open("rb") as handle:
            return handle.read(size)
    return b""


def matches_declared_type(content_type: str, header: bytes) -> bool:
    """True when ``header`` matches the declared image content type."""
    if content_type == "image/webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if content_type in {"image/heic", "image/heif"}:
        return len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in HEIF_BRANDS
    prefixes = PREFIXES.get(content_type)
    return bool(prefixes) and any(header.startswith(item) for item in prefixes)
