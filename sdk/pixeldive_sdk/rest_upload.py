"""Streaming REST upload from a filesystem path (PERF-004)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from pixeldive_sdk.ids import resource_id


class RestPathUploadMixin:
    """POST multipart from a file handle without buffering the whole blob."""

    _http: httpx.AsyncClient

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
            response = await self._http.post(
                f"/api/v1/sessions/{resource_id(session_id)}/images",
                files={"file": (filename or source.name, handle, content_type)},
                data=data,
            )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
