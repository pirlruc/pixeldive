"""FastAPI REST endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import JPEG_MIN, PNG_1X1, sample_create


def _session_json() -> dict:
    """JSON body for POST /sessions."""
    return sample_create().model_dump(mode="json", by_alias=True)


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Liveness endpoint returns ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_session_crud(client: AsyncClient) -> None:
    """Create, get, update, and delete a session over REST."""
    created = await client.post("/api/v1/sessions", json=_session_json())
    assert created.status_code == 201
    body = created.json()
    session_id = body["id"]
    assert body["status"] == "CREATED"
    assert body["metadata"]["capture_mode"] == "burst"
    assert body["phone_info"]["sdk_int"] == 34

    fetched = await client.get(f"/api/v1/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session_name"] == "capture-run"

    updated = await client.put(
        f"/api/v1/sessions/{session_id}",
        json={"status": "COMPLETED", "metadata": {"k": "v"}},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "COMPLETED"

    missing = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert missing.status_code == 404

    deleted = await client.delete(f"/api/v1/sessions/{session_id}")
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/sessions/{session_id}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_invalid_status_and_payload(client: AsyncClient) -> None:
    """Unknown status and incomplete bodies are 422."""
    created = await client.post("/api/v1/sessions", json=_session_json())
    session_id = created.json()["id"]
    bad_status = await client.put(f"/api/v1/sessions/{session_id}", json={"status": "NOPE"})
    assert bad_status.status_code == 422
    incomplete = await client.post("/api/v1/sessions", json={"session_name": "x"})
    assert incomplete.status_code == 422


@pytest.mark.asyncio
async def test_upload_list_download_batch(client: AsyncClient) -> None:
    """Single and batch multipart uploads plus binary download."""
    created = await client.post("/api/v1/sessions", json=_session_json())
    session_id = created.json()["id"]

    single = await client.post(
        f"/api/v1/sessions/{session_id}/images",
        files={"file": ("frame.png", PNG_1X1, "image/png")},
        data={"metadata": '{"iso": 200}'},
    )
    assert single.status_code == 201
    image_id = single.json()["id"]
    assert single.json()["metadata"]["iso"] == 200

    listed = await client.get(f"/api/v1/sessions/{session_id}/images")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    download = await client.get(f"/api/v1/sessions/{session_id}/images/{image_id}")
    assert download.status_code == 200
    assert download.content == PNG_1X1
    assert download.headers["content-type"].startswith("image/png")

    batch = await client.post(
        f"/api/v1/sessions/{session_id}/images/batch",
        files=[
            ("files", ("a.jpg", JPEG_MIN, "image/jpeg")),
            ("files", ("b.png", PNG_1X1, "image/png")),
        ],
        data={"metadata": '{"batch": true}'},
    )
    assert batch.status_code == 201
    assert len(batch.json()) == 2

    missing_image = await client.get(f"/api/v1/sessions/{session_id}/images/{uuid.uuid4()}")
    assert missing_image.status_code == 404


@pytest.mark.asyncio
async def test_upload_rejects_non_image_and_bad_metadata(client: AsyncClient) -> None:
    """text/plain and non-object metadata are 422."""
    created = await client.post("/api/v1/sessions", json=_session_json())
    session_id = created.json()["id"]
    text = await client.post(
        f"/api/v1/sessions/{session_id}/images",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert text.status_code == 422
    bad_meta = await client.post(
        f"/api/v1/sessions/{session_id}/images",
        files={"file": ("frame.png", PNG_1X1, "image/png")},
        data={"metadata": "[1,2]"},
    )
    assert bad_meta.status_code == 422


@pytest.mark.asyncio
async def test_upload_too_large(client: AsyncClient, service) -> None:
    """Payloads over max_image_bytes are 413."""
    created = await client.post("/api/v1/sessions", json=_session_json())
    session_id = created.json()["id"]
    huge = b"P" * (service._settings.max_image_bytes + 1)
    response = await client.post(
        f"/api/v1/sessions/{session_id}/images",
        files={"file": ("big.png", huge, "image/png")},
    )
    assert response.status_code == 413
