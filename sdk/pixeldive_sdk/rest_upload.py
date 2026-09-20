"""Streaming REST upload from a filesystem path (PERF-004)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pixeldive_sdk.ids import resource_id
from pixeldive_sdk.rest_http import RestHttpMixin


class RestPathUploadMixin(RestHttpMixin):
    """POST multipart from a file handle without buffering the whole blob."""

    async def upload_image_from_path(
        self,
        session_id: str,
        path: str | Path,
        *,
        filename: str | None = None,
        content_type: str = "image/png",
        metadata: str | None = None,
    ) -> dict[str, Any]:
        """POST multipart from a file path without buffering the whole file."""
        source = Path(path)
        data: dict[str, str] = {}
        if metadata is not None:
            data["metadata"] = metadata
        with source.open("rb") as handle:
            result: dict[str, Any] = await self._json(
                "POST",
                f"/api/v1/sessions/{resource_id(session_id)}/images",
                files={"file": (filename or source.name, handle, content_type)},
                data=data,
            )
        return result
