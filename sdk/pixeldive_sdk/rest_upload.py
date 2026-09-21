"""Streaming REST upload from a filesystem path (PERF-004)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, BinaryIO

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
        with source.open("rb") as handle:
            result: dict[str, Any] = await self._json(
                "POST",
                f"/api/v1/sessions/{resource_id(session_id)}/images",
                files={"file": (filename or source.name, handle, content_type)},
                data=self._form_fields(metadata),
            )
        return result

    async def upload_images_batch_from_paths(
        self,
        session_id: str,
        items: Sequence[tuple[str | Path, str | None, str]],
        metadata: str | None = None,
    ) -> list[dict[str, Any]]:
        """POST multipart batch from file handles without buffering whole files."""
        handles: list[BinaryIO] = []
        try:
            files = [self._open_batch_file(item, handles) for item in items]
            result: list[dict[str, Any]] = await self._json(
                "POST",
                f"/api/v1/sessions/{resource_id(session_id)}/images/batch",
                files=files,
                data=self._form_fields(metadata),
            )
            return result
        finally:
            for handle in handles:
                handle.close()

    def _open_batch_file(
        self,
        item: tuple[str | Path, str | None, str],
        handles: list[BinaryIO],
    ) -> tuple[str, tuple[str, BinaryIO, str]]:
        """Open one batch path and track the handle for later close."""
        path, filename, content_type = item
        source = Path(path)
        handle = source.open("rb")
        handles.append(handle)
        return ("files", (filename or source.name, handle, content_type))
