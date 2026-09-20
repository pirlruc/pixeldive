"""Android SDK fixture and Android-shaped payload contract."""

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
    / "android"
    / "sdk"
    / "src"
    / "main"
    / "resources"
    / "sample_android_session.json"
)
DEMO_ROOT = (
    Path(__file__).resolve().parents[1]
    / "android"
    / "demo"
    / "src"
    / "main"
    / "kotlin"
    / "com"
    / "pixeldive"
    / "demo"
)


def _load_android_fixture() -> dict:
    """Return the bundled Pixel session JSON."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_android_fixture_exists_and_is_android_shaped() -> None:
    """The Kotlin sample uses the same keys Android clients send."""
    payload = _load_android_fixture()
    assert payload["phone_info"]["manufacturer"] == "Google"
    assert payload["phone_info"]["android_version"] == "15"
    assert payload["phone_info"]["sdk_int"] == 35
    assert payload["camera_capabilities"]["camera_count"] == 2
    assert payload["camera_capabilities"]["camera_count"] == len(
        payload["camera_capabilities"]["cameras"]
    )
    assert payload["metadata"]["platform"] == "android"
    assert payload["metadata"]["source"] == "pixeldive-android-sdk"


def test_android_fixture_validates_session_create() -> None:
    """SessionCreate accepts the Android SDK fixture without schema changes."""
    created = SessionCreate.model_validate(_load_android_fixture())
    dumped = created.model_dump(mode="json", by_alias=True)
    assert dumped["phone_info"]["sdk_int"] == 35
    assert dumped["metadata"]["platform"] == "android"
    assert "storage_path" not in dumped


@pytest.mark.asyncio
async def test_android_fixture_round_trip(client: AsyncClient) -> None:
    """Create, upload, and download through REST using the Android payload."""
    created = await client.post("/api/v1/sessions", json=_load_android_fixture())
    assert created.status_code == 201
    body = created.json()
    assert body["phone_info"]["brand"] == "google"
    assert body["metadata"]["platform"] == "android"
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


def test_android_demo_uses_sdk_only() -> None:
    """The Compose demo talks to pixeldive through PixeldiveClient."""
    sources = list(DEMO_ROOT.glob("*.kt"))
    assert sources
    joined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    assert "PixeldiveClient" in joined
    assert "DeviceSnapshot" in joined
    assert "AndroidDeviceProbe" in joined
    assert "OkHttpClient(" not in joined
    assert "SharedPreferences" not in joined
    manifest = (DEMO_ROOT.parents[3] / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'usesCleartextTraffic="true"' not in manifest
    assert "networkSecurityConfig" in manifest


def test_kotlin_threshold_reader() -> None:
    """CI-022 reader loads the Kotlin consumer copy."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "read_kotlin_threshold.py"), "statement_coverage"],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert int(result.stdout.strip()) >= 95


def test_android_check_script_enforces_kover() -> None:
    """KT-TEST-002 is wired through Gradle koverVerify, not a log-only echo."""
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "check-android-sdk.sh").read_text(encoding="utf-8")
    assert ":sdk:koverVerify" in script
    assert ":sdk:ktlintCheck" in script
    assert ":sdk:detekt" in script
