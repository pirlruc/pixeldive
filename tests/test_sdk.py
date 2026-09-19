"""Python SDK and demo app."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from pixeldive_sdk import GrpcClient, RestClient, sample_session_payload

from app.api import create_app
from app.grpc_server import start_grpc_server
from app.service import SessionService
from demo.app import asgi_client_for, create_demo_app
from tests.conftest import PNG_1X1


@pytest.mark.asyncio
async def test_rest_sdk_round_trip(service: SessionService) -> None:
    """RestClient creates, lists, uploads, and downloads through the ASGI app."""
    app = create_app(service)
    transport = ASGITransport(app=app)
    http = AsyncClient(transport=transport, base_url="http://test")
    async with RestClient("http://test", client=http) as client:
        assert (await client.health())["status"] == "ok"
        assert (await client.ready())["status"] == "ok"
        created = await client.create_session(sample_session_payload("sdk-run"))
        session_id = created["id"]
        listed = await client.list_sessions(limit=10)
        assert any(item["id"] == session_id for item in listed["items"])
        image = await client.upload_image(
            session_id, "frame.png", PNG_1X1, "image/png", '{"iso": 64}'
        )
        assert "storage_path" not in image
        images = await client.list_images(session_id)
        assert len(images["items"]) == 1
        payload = b"".join(
            [chunk async for chunk in client.download_image(session_id, image["id"])]
        )
        assert payload == PNG_1X1
        updated = await client.update_session(
            session_id, {"metadata": {"k": "v"}}, merge_metadata=True
        )
        assert updated["metadata"]["source"] == "pixeldive-demo"
        await client.delete_session(session_id)


@pytest.mark.asyncio
async def test_rest_sdk_rejects_non_uuid_ids() -> None:
    """Path ids must be UUIDs so callers cannot inject extra URL segments."""
    from pixeldive_sdk.ids import resource_id

    with pytest.raises(ValueError):
        resource_id("../secret")
    with pytest.raises(ValueError):
        resource_id("not-a-uuid")


@pytest.mark.asyncio
async def test_demo_app_uses_sdk(service: SessionService) -> None:
    """Demo UI and JSON routes talk to pixeldive through RestClient."""
    backend = create_app(service)
    sdk = asgi_client_for(backend)
    demo = create_demo_app(sdk)
    transport = ASGITransport(app=demo)
    async with AsyncClient(transport=transport, base_url="http://demo") as http:
        page = await http.get("/")
        assert page.status_code == 200
        assert "pixeldive capture demo" in page.text
        health = await http.get("/api/health")
        assert health.status_code == 200
        created = await http.post("/api/sessions")
        assert created.status_code == 200
        session_id = created.json()["id"]
        listed = await http.get("/api/sessions")
        assert listed.json()["items"]
        uploaded = await http.post(
            f"/api/sessions/{session_id}/images",
            files={"file": ("frame.png", PNG_1X1, "image/png")},
        )
        assert uploaded.status_code == 200
        images = await http.get(f"/api/sessions/{session_id}/images")
        image_id = images.json()["items"][0]["id"]
        download = await http.get(f"/api/sessions/{session_id}/images/{image_id}/download")
        assert download.status_code == 200
        assert download.content == PNG_1X1
        missing = await http.get(
            f"/api/sessions/{session_id}/images/00000000-0000-0000-0000-000000000000/download"
        )
        assert missing.status_code == 404
        deleted = await http.delete(f"/api/sessions/{session_id}")
        assert deleted.status_code == 200
        gone = await http.get("/api/sessions/00000000-0000-0000-0000-000000000000/images")
        assert gone.status_code == 404
    await sdk.aclose()


@pytest.mark.asyncio
async def test_grpc_sdk_create_and_upload(service: SessionService) -> None:
    """GrpcClient can create a session and upload an image."""
    server, port = await start_grpc_server(service, "127.0.0.1", 0)
    async with GrpcClient(f"127.0.0.1:{port}") as client:
        session = await client.create_session()
        listed = await client.list_sessions()
        assert listed.sessions
        image = await client.upload_image(session.id, "frame.png", PNG_1X1)
        assert image.size_bytes == len(PNG_1X1)
    with pytest.raises(RuntimeError, match="connect"):
        client._require_stub()
    await server.stop(grace=0)
