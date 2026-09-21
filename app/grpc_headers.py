"""Shared filename/type/metadata defaults for gRPC image chunks."""

from __future__ import annotations

from typing import Any

from app.metadata import parse_metadata_json


def chunk_headers(
    filename: str,
    content_type: str,
    metadata_json: str,
) -> tuple[str, str, dict[str, Any]]:
    """Fill defaults used by single and batch upload streams."""
    return (
        filename or "upload.bin",
        content_type or "application/octet-stream",
        parse_metadata_json(metadata_json or None),
    )
