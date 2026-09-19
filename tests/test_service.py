"""SessionService business rules."""

from __future__ import annotations

import uuid

import pytest

from app.exceptions import (
    BatchLimitError,
    ImageNotFoundError,
    ImageTooLargeError,
    InvalidMetadataError,
    SessionNotFoundError,
    UnsupportedContentTypeError,
)
from app.metadata import parse_metadata_json
from app.models import ImageUpload, SessionStatus, SessionUpdate
from app.service import SessionService
from tests.conftest import PNG_1X1, sample_create


@pytest.mark.asyncio
async def test_create_and_get_session(service: SessionService) -> None:
    """Created sessions persist Android device JSON."""
    created = await service.create_session(sample_create())
    loaded = await service.get_session(created.id)
    assert loaded.session_name == "capture-run"
    assert loaded.status == SessionStatus.CREATED.value
    assert loaded.phone_info.model == "Pixel 8"
    assert loaded.camera_capabilities.camera_count == 2
    assert loaded.extra_metadata["capture_mode"] == "burst"


@pytest.mark.asyncio
async def test_get_missing_session(service: SessionService) -> None:
    """Unknown UUIDs raise SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError):
        await service.get_session(uuid.uuid4())


@pytest.mark.asyncio
async def test_update_status_and_metadata(service: SessionService) -> None:
    """PUT-style patches update status and merge-replace metadata."""
    created = await service.create_session(sample_create())
    updated = await service.update_session(
        created.id,
        SessionUpdate(status=SessionStatus.COMPLETED, extra_metadata={"note": "done"}),
    )
    assert updated.status == "COMPLETED"
    assert updated.extra_metadata == {"note": "done"}


@pytest.mark.asyncio
async def test_add_image_marks_in_progress(service: SessionService) -> None:
    """First upload moves CREATED → IN_PROGRESS."""
    session = await service.create_session(sample_create())
    image = await service.add_image(
        session.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    loaded = await service.get_session(session.id)
    assert loaded.status == SessionStatus.IN_PROGRESS.value
    assert image.size_bytes == len(PNG_1X1)
    listed = await service.list_images(session.id)
    assert len(listed.items) == 1


@pytest.mark.asyncio
async def test_batch_dedup_and_delete_gc(service: SessionService, storage) -> None:
    """Identical payloads share a path; session delete GCs when refcount hits 0."""
    first = await service.create_session(sample_create(session_name="a"))
    second = await service.create_session(sample_create(session_name="b"))
    uploads = [
        ImageUpload(filename="a.png", content_type="image/png", payload=PNG_1X1),
        ImageUpload(filename="b.png", content_type="image/png", payload=PNG_1X1),
    ]
    images = await service.add_images_batch(first.id, uploads)
    assert images[0].storage_path == images[1].storage_path
    shared = images[0].storage_path
    other = await service.add_image(
        second.id,
        ImageUpload(filename="c.png", content_type="image/png", payload=PNG_1X1),
    )
    assert other.storage_path == shared
    await service.delete_session(first.id)
    assert await storage.exists(shared)
    await service.delete_session(second.id)
    assert not await storage.exists(shared)


@pytest.mark.asyncio
async def test_stream_image_and_missing(service: SessionService) -> None:
    """Streaming returns original bytes; unknown image ids 404."""
    session = await service.create_session(sample_create())
    image = await service.add_image(
        session.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    payload = b"".join([chunk async for chunk in service.stream_image(session.id, image.id)])
    assert payload == PNG_1X1
    with pytest.raises(ImageNotFoundError):
        await service.get_image(session.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_reject_bad_content_type(service: SessionService) -> None:
    """Non-image types are rejected before disk writes."""
    session = await service.create_session(sample_create())
    with pytest.raises(UnsupportedContentTypeError):
        await service.add_image(
            session.id,
            ImageUpload(filename="note.txt", content_type="text/plain", payload=b"hi"),
        )


@pytest.mark.asyncio
async def test_update_name_only_and_too_large(service: SessionService) -> None:
    """Name-only patch skips status; oversized payloads are rejected."""
    session = await service.create_session(sample_create())
    updated = await service.update_session(session.id, SessionUpdate(session_name="renamed"))
    assert updated.session_name == "renamed"
    assert updated.status == SessionStatus.CREATED.value
    with pytest.raises(ImageTooLargeError):
        await service.add_image(
            session.id,
            ImageUpload(
                filename="big.png",
                content_type="image/png",
                payload=b"x" * (service._settings.max_image_bytes + 1),
            ),
        )


def test_parse_metadata_json() -> None:
    """Empty/object JSON is accepted; arrays are not."""
    assert parse_metadata_json(None) == {}
    assert parse_metadata_json('{"iso": 100}') == {"iso": 100}
    with pytest.raises(InvalidMetadataError):
        parse_metadata_json("[1]")


@pytest.mark.asyncio
async def test_batch_limit_and_empty(service: SessionService) -> None:
    """Empty batches and oversized batches are rejected before writes."""
    session = await service.create_session(sample_create())
    with pytest.raises(BatchLimitError):
        await service.add_images_batch(session.id, [])
    service._settings.max_batch_images = 1
    uploads = [
        ImageUpload(filename="a.png", content_type="image/png", payload=PNG_1X1),
        ImageUpload(filename="b.png", content_type="image/png", payload=PNG_1X1),
    ]
    with pytest.raises(BatchLimitError):
        await service.add_images_batch(session.id, uploads)


@pytest.mark.asyncio
async def test_missing_blob_maps_to_image_not_found(service: SessionService, storage) -> None:
    """A deleted blob with a leftover row is ImageNotFoundError on stream."""
    session = await service.create_session(sample_create())
    image = await service.add_image(
        session.id,
        ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
    )
    await storage.delete(image.storage_path)
    with pytest.raises(ImageNotFoundError):
        async for _ in service.stream_image(session.id, image.id):
            pass


@pytest.mark.asyncio
async def test_add_image_requires_session_before_persist(service: SessionService, storage) -> None:
    """Missing sessions do not leave content-addressed blobs."""
    with pytest.raises(SessionNotFoundError):
        await service.add_image(
            uuid.uuid4(),
            ImageUpload(filename="frame.png", content_type="image/png", payload=PNG_1X1),
        )
    assert await storage.list_blobs() == []


@pytest.mark.asyncio
async def test_invalid_type_discards_spool(service: SessionService, tmp_path) -> None:
    """Validation failures still delete the incoming spool file."""
    session = await service.create_session(sample_create())
    spool = tmp_path / "images" / ".incoming" / "partial.part"
    spool.parent.mkdir(parents=True, exist_ok=True)
    spool.write_bytes(b"hi")
    with pytest.raises(UnsupportedContentTypeError):
        await service.add_image(
            session.id,
            ImageUpload(
                filename="note.txt",
                content_type="text/plain",
                payload=b"",
                spool_path=str(spool),
                digest_hex="ab",
                size_bytes=2,
            ),
        )
    assert not spool.exists()
