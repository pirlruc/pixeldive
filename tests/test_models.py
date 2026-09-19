"""SQLModel nested JSON and status helpers."""

from app.models import CameraCapabilities, PhoneInfo, SessionStatus
from tests.conftest import sample_create, sample_phone_info


def test_phone_info_android_field_names() -> None:
    """Android Build keys round-trip through the schema."""
    info = sample_phone_info()
    dumped = info.model_dump()
    assert dumped["manufacturer"] == "Google"
    assert dumped["sdk_int"] == 34
    assert PhoneInfo.model_validate(dumped).model == "Pixel 8"


def test_session_create_metadata_alias() -> None:
    """Clients send ``metadata``; the model stores extra_metadata."""
    payload = sample_create()
    assert payload.extra_metadata["capture_mode"] == "burst"
    dumped = payload.model_dump(by_alias=True)
    assert dumped["metadata"]["capture_mode"] == "burst"


def test_session_status_values() -> None:
    """Only the documented lifecycle strings are allowed."""
    assert {item.value for item in SessionStatus} == {
        "CREATED",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
    }


def test_camera_count_rejects_negative() -> None:
    """camera_count must be non-negative."""
    try:
        CameraCapabilities(camera_count=-1, cameras=[])
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_promote_metadata_leaves_explicit_extra_alone() -> None:
    """When extra_metadata is already set, the helper does not rewrite the dict."""
    from app.metadata import promote_metadata

    original = {"metadata": {"a": 1}, "extra_metadata": {"b": 2}}
    assert promote_metadata(original)["extra_metadata"] == {"b": 2}
    assert promote_metadata("plain") == "plain"


def test_sanitize_filename_strips_paths_and_header_metacharacters() -> None:
    """Download names cannot smuggle paths, quotes, or CR/LF."""
    from app.filenames import sanitize_filename

    assert sanitize_filename('../../evil\r\nX: 1".png') == "evilX: 1.png"
    assert sanitize_filename(None) == "upload.bin"
    assert sanitize_filename("   ") == "upload.bin"
