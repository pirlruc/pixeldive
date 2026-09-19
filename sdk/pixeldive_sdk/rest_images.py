"""Image upload/list/download methods for ``RestClient``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from pixeldive_sdk.ids import resource_id


class RestImageMixin:
    """Image routes under ``/api/v1/sessions/{id}/images``."""

    _http: httpx.AsyncClient

    async def upload_image(
        self,
        session_id: str,
        filename: str,
        payload: bytes,
        content_type: str = "image/png",
        metadata: str | None = None,
    ) -> dict[str, Any]:
        """POST multipart /api/v1/sessions/{id}/images."""
        data: dict[str, str] = {}
        if metadata is not None:
            data["metadata"] = metadata
        response = await self._http.post(
            f"/api/v1/sessions/{resource_id(session_id)}/images",
            files={"file": (filename, payload, content_type)},
            data=data,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def list_images(
        self,
        session_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/sessions/{id}/images."""
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        response = await self._http.get(
            f"/api/v1/sessions/{resource_id(session_id)}/images",
            params=params,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def download_image(self, session_id: str, image_id: str) -> AsyncIterator[bytes]:
        """Stream GET /api/v1/sessions/{id}/images/{image_id}."""
        async with self._http.stream(
            "GET",
            f"/api/v1/sessions/{resource_id(session_id)}/images/{resource_id(image_id)}",
        ) as response:
            if response.status_code >= 400:
                await response.aread()
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
