"""Image upload/list/download methods for ``RestClient``."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from pixeldive_sdk.ids import resource_id
from pixeldive_sdk.rest_http import RestHttpMixin


class RestImageMixin(RestHttpMixin):
    """Image routes under ``/api/v1/sessions/{id}/images``."""

    async def upload_image(
        self,
        session_id: str,
        filename: str,
        payload: bytes,
        content_type: str = "image/png",
        metadata: str | None = None,
    ) -> dict[str, Any]:
        """POST multipart /api/v1/sessions/{id}/images."""
        result: dict[str, Any] = await self._json(
            "POST",
            f"/api/v1/sessions/{resource_id(session_id)}/images",
            files={"file": (filename, payload, content_type)},
            data=self._form_fields(metadata),
        )
        return result

    async def upload_images_batch(
        self,
        session_id: str,
        items: Sequence[tuple[str, bytes, str]],
        metadata: str | None = None,
    ) -> list[dict[str, Any]]:
        """POST multipart /api/v1/sessions/{id}/images/batch."""
        files = [("files", (name, blob, content_type)) for name, blob, content_type in items]
        result: list[dict[str, Any]] = await self._json(
            "POST",
            f"/api/v1/sessions/{resource_id(session_id)}/images/batch",
            files=files,
            data=self._form_fields(metadata),
        )
        return result

    async def list_images(
        self,
        session_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/sessions/{id}/images."""
        payload: dict[str, Any] = await self._json(
            "GET",
            f"/api/v1/sessions/{resource_id(session_id)}/images",
            params=self._page_params(limit, cursor),
        )
        return payload

    async def download_image(self, session_id: str, image_id: str) -> AsyncIterator[bytes]:
        """Stream GET /api/v1/sessions/{id}/images/{image_id}."""
        headers = self._auth_headers()
        async with self._http.stream(
            "GET",
            f"/api/v1/sessions/{resource_id(session_id)}/images/{resource_id(image_id)}",
            headers=headers,
        ) as response:
            if response.status_code >= 400:
                await response.aread()
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
