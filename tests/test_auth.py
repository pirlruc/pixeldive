"""Authentication and session ownership (SEC-001)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import create_app
from tests.conftest import PNG_1X1, sample_create
from tests.factories import auth_settings, make_service


def _session_json() -> dict:
    """JSON body for POST /sessions."""
    return sample_create(session_name="owned").model_dump(mode="json", by_alias=True)


@pytest.mark.asyncio
async def test_rest_auth_and_tenant_isolation(tmp_path: Path) -> None:
    """Missing tokens are 401; another tenant is 404 (SEC-003)."""
    settings = auth_settings(tmp_path)
    service, engine = await make_service(settings)
    app = create_app(service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        unauth = await http.post("/api/v1/sessions", json=_session_json())
        assert unauth.status_code == 401
        created = await http.post(
            "/api/v1/sessions",
            json=_session_json(),
            headers={"Authorization": "Bearer alpha"},
        )
        assert created.status_code == 201
        session_id = created.json()["id"]
        other = await http.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": "Bearer beta"},
        )
        assert other.status_code == 404
        owner = await http.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": "Bearer alpha"},
        )
        assert owner.status_code == 200
        upload = await http.post(
            f"/api/v1/sessions/{session_id}/images",
            files={"file": ("frame.png", PNG_1X1, "image/png")},
            headers={"Authorization": "Bearer alpha"},
        )
        assert upload.status_code == 201
        listed = await http.get("/api/v1/sessions", headers={"Authorization": "Bearer beta"})
        assert listed.json()["items"] == []
        before = {path for path in (tmp_path / "images").rglob("*") if path.is_file()}
        foreign = await http.post(
            f"/api/v1/sessions/{session_id}/images",
            files={"file": ("frame.png", PNG_1X1, "image/png")},
            headers={"Authorization": "Bearer beta"},
        )
        assert foreign.status_code == 404
        after = {path for path in (tmp_path / "images").rglob("*") if path.is_file()}
        assert after == before
    await engine.dispose()
