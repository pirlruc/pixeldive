"""iOS SDK fixture and Android-shaped payload contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.models import SessionCreate
from tests.conftest import PNG_1X1

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "ios"
    / "Sources"
    / "PixeldiveSDK"
    / "Fixtures"
    / "sample_ios_session.json"
)
DEMO_ROOT = Path(__file__).resolve().parents[1] / "ios" / "Demo"


def _load_ios_fixture() -> dict:
    """Return the bundled iPhone session JSON."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_ios_fixture_exists_and_is_android_shaped() -> None:
    """The Swift sample uses the same keys Android clients send."""
    payload = _load_ios_fixture()
    assert payload["phone_info"]["manufacturer"] == "Apple"
    assert payload["phone_info"]["android_version"] == "18.6"
    assert payload["phone_info"]["sdk_int"] == 18
    assert payload["camera_capabilities"]["camera_count"] == 2
    assert payload["camera_capabilities"]["camera_count"] == len(
        payload["camera_capabilities"]["cameras"]
    )
    assert payload["metadata"]["platform"] == "ios"
    assert payload["metadata"]["source"] == "pixeldive-ios-sdk"


def test_ios_fixture_validates_session_create() -> None:
    """SessionCreate accepts the iOS SDK fixture without schema changes."""
    created = SessionCreate.model_validate(_load_ios_fixture())
    dumped = created.model_dump(mode="json", by_alias=True)
    assert dumped["phone_info"]["sdk_int"] == 18
    assert dumped["metadata"]["platform"] == "ios"
    assert "storage_path" not in dumped


@pytest.mark.asyncio
async def test_ios_fixture_round_trip(client: AsyncClient) -> None:
    """Create, upload, and download through REST using the iOS payload."""
    created = await client.post("/api/v1/sessions", json=_load_ios_fixture())
    assert created.status_code == 201
    body = created.json()
    assert body["phone_info"]["brand"] == "apple"
    assert body["metadata"]["platform"] == "ios"
    session_id = body["id"]
    uploaded = await client.post(
        f"/api/v1/sessions/{session_id}/images",
        files={"file": ("frame.png", PNG_1X1, "image/png")},
    )
    assert uploaded.status_code == 201
    assert "storage_path" not in uploaded.json()
    image_id = uploaded.json()["id"]
    download = await client.get(f"/api/v1/sessions/{session_id}/images/{image_id}")
    assert download.status_code == 200
    assert download.content == PNG_1X1


def test_ios_demo_uses_sdk_only() -> None:
    """The SwiftUI demo talks to pixeldive through PixeldiveClient."""
    sources = list(DEMO_ROOT.glob("*.swift"))
    assert sources
    joined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    assert "PixeldiveClient" in joined
    assert "DeviceSnapshot" in joined
    assert "URLSession.shared.data" not in joined
    assert "UserDefaults" not in joined


def test_swift_threshold_reader() -> None:
    """CI-022 reader loads the Swift consumer copy."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "read_swift_threshold.py"), "statement_coverage"],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert int(result.stdout.strip()) >= 90
