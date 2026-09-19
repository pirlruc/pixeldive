"""gRPC SessionService servicer."""

from __future__ import annotations

import uuid

import grpc
import pytest
import pytest_asyncio

from app.grpc_server import SessionServicer, start_grpc_server
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.service import SessionService
from tests.conftest import PNG_1X1, sample_cameras, sample_phone_caps, sample_phone_info


def _create_request() -> pb.CreateSessionRequest:
    """Build a protobuf create request from Android-shaped samples."""
    info = sample_phone_info().model_dump()
    caps = sample_phone_caps().model_dump()
    cameras = sample_cameras()
    from google.protobuf.struct_pb2 import Struct

    metadata = Struct()
    metadata.update({"capture_mode": "burst"})
    return pb.CreateSessionRequest(
        session_name="grpc-run",
        phone_info=pb.PhoneInfo(**info),
        phone_capabilities=pb.PhoneCapabilities(**caps),
        camera_capabilities=pb.CameraCapabilities(
            camera_count=cameras.camera_count,
            cameras=[pb.CameraInfo(**item.model_dump()) for item in cameras.cameras],
        ),
        metadata=metadata,
    )


@pytest_asyncio.fixture
async def stub(service: SessionService):
    """In-process aio server on an ephemeral port."""
    server, port = await start_grpc_server(service, "127.0.0.1", 0)
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    try:
        yield pb_grpc.SessionServiceStub(channel)
    finally:
        await channel.close()
        await server.stop(grace=0)


@pytest.mark.asyncio
async def test_grpc_crud_and_images(stub) -> None:
    """Create/get/update/list/upload/download/delete over gRPC."""
    created = await stub.CreateSession(_create_request())
    session_id = created.session.id
    assert created.session.status == "CREATED"
    assert created.session.phone_info.model == "Pixel 8"
    assert created.session.metadata["capture_mode"] == "burst"

    fetched = await stub.GetSession(pb.GetSessionRequest(session_id=session_id))
    assert fetched.session.session_name == "grpc-run"

    listed_sessions = await stub.ListSessions(pb.ListSessionsRequest(limit=10))
    assert any(item.id == session_id for item in listed_sessions.sessions)

    updated = await stub.UpdateSession(
        pb.UpdateSessionRequest(session_id=session_id, status="COMPLETED"),
    )
    assert updated.session.status == "COMPLETED"

    async def single_chunks():
        yield pb.ImageChunk(
            session_id=session_id,
            filename="frame.png",
            content_type="image/png",
            data=PNG_1X1[:10],
            metadata_json='{"iso": 64}',
        )
        yield pb.ImageChunk(data=PNG_1X1[10:])

    uploaded = await stub.UploadImage(single_chunks())
    image_id = uploaded.image.id
    assert uploaded.image.size_bytes == len(PNG_1X1)

    listed = await stub.ListSessionImages(pb.ListImagesRequest(session_id=session_id))
    assert len(listed.images) == 1

    chunks = stub.DownloadImage(pb.DownloadImageRequest(session_id=session_id, image_id=image_id))
    payload = b"".join([item.data async for item in chunks])
    assert payload == PNG_1X1

    async def batch_chunks():
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=0,
            filename="a.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=True,
        )
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=1,
            filename="b.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=True,
        )

    batched = await stub.UploadImagesBatch(batch_chunks())
    assert len(batched.images) == 2

    deleted = await stub.DeleteSession(pb.DeleteSessionRequest(session_id=session_id))
    assert deleted.deleted is True

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetSession(pb.GetSessionRequest(session_id=session_id))
    assert err.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_mapped_service_errors(stub) -> None:
    """Create/update/upload validation failures map to INVALID_ARGUMENT."""
    with pytest.raises(grpc.aio.AioRpcError) as create_err:
        await stub.CreateSession(pb.CreateSessionRequest(session_name=""))
    assert create_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    created = await stub.CreateSession(_create_request())
    session_id = created.session.id
    with pytest.raises(grpc.aio.AioRpcError) as upd_err:
        await stub.UpdateSession(
            pb.UpdateSessionRequest(session_id=session_id, status="NOPE"),
        )
    assert upd_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def not_image():
        yield pb.ImageChunk(
            session_id=session_id,
            filename="note.txt",
            content_type="text/plain",
            data=b"hello",
        )

    with pytest.raises(grpc.aio.AioRpcError) as up_err:
        await stub.UploadImage(not_image())
    assert up_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def not_image_batch():
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=0,
            filename="note.txt",
            content_type="text/plain",
            data=b"hello",
            end_of_image=True,
        )

    with pytest.raises(grpc.aio.AioRpcError) as batch_err:
        await stub.UploadImagesBatch(not_image_batch())
    assert batch_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_grpc_rejects_oversize_and_batch_cap(stub, service: SessionService) -> None:
    """Assembly aborts when bytes or cardinality exceed settings."""
    created = await stub.CreateSession(_create_request())
    session_id = created.session.id
    service._settings.max_image_bytes = 8

    async def huge():
        yield pb.ImageChunk(
            session_id=session_id,
            filename="frame.png",
            content_type="image/png",
            data=PNG_1X1,
        )

    with pytest.raises(grpc.aio.AioRpcError) as huge_err:
        await stub.UploadImage(huge())
    assert huge_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def huge_batch():
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=0,
            filename="a.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=True,
        )

    with pytest.raises(grpc.aio.AioRpcError) as huge_batch_err:
        await stub.UploadImagesBatch(huge_batch())
    assert huge_batch_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    service._settings.max_image_bytes = 1024 * 1024
    service._settings.max_batch_images = 1

    async def two():
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=0,
            filename="a.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=True,
        )
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=1,
            filename="b.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=True,
        )

    with pytest.raises(grpc.aio.AioRpcError) as cap_err:
        await stub.UploadImagesBatch(two())
    assert cap_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_grpc_invalid_uuid(stub) -> None:
    """Malformed UUIDs are INVALID_ARGUMENT."""
    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetSession(pb.GetSessionRequest(session_id="not-a-uuid"))
    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_servicer_direct_missing(service: SessionService) -> None:
    """Servicer maps SessionNotFoundError without a real socket."""
    servicer = SessionServicer(service)
    context = _FakeContext()
    with pytest.raises(RuntimeError):
        await servicer.GetSession(
            pb.GetSessionRequest(session_id=str(uuid.uuid4())),
            context,  # type: ignore[arg-type]
        )
    assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_error_paths(stub, service: SessionService) -> None:
    """Empty streams, partial batches, and missing resources map to gRPC codes."""
    created = await stub.CreateSession(_create_request())
    session_id = created.session.id

    async def empty():
        if False:
            yield pb.ImageChunk()

    with pytest.raises(grpc.aio.AioRpcError) as empty_err:
        await stub.UploadImage(empty())
    assert empty_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def no_session():
        yield pb.ImageChunk(filename="x.png", content_type="image/png", data=PNG_1X1)

    with pytest.raises(grpc.aio.AioRpcError) as ns_err:
        await stub.UploadImage(no_session())
    assert ns_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def empty_batch():
        if False:
            yield pb.BatchImageChunk()

    with pytest.raises(grpc.aio.AioRpcError) as eb_err:
        await stub.UploadImagesBatch(empty_batch())
    assert eb_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def batch_no_session():
        yield pb.BatchImageChunk(
            filename="a.png", content_type="image/png", data=PNG_1X1, end_of_image=True
        )

    with pytest.raises(grpc.aio.AioRpcError) as bns:
        await stub.UploadImagesBatch(batch_no_session())
    assert bns.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    async def partial_batch():
        yield pb.BatchImageChunk(
            session_id=session_id,
            image_index=0,
            filename="a.png",
            content_type="image/png",
            data=PNG_1X1,
            end_of_image=False,
            metadata_json='{"iso": 1}',
        )

    with pytest.raises(grpc.aio.AioRpcError) as partial:
        await stub.UploadImagesBatch(partial_batch())
    assert partial.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    renamed = await stub.UpdateSession(
        pb.UpdateSessionRequest(session_id=session_id, session_name="renamed"),
    )
    assert renamed.session.session_name == "renamed"

    from google.protobuf.struct_pb2 import Struct

    extra = Struct()
    extra.update({"merged": True})
    merged = await stub.UpdateSession(
        pb.UpdateSessionRequest(session_id=session_id, metadata=extra, merge_metadata=True),
    )
    assert merged.session.metadata["merged"] is True
    cleared = await stub.UpdateSession(
        pb.UpdateSessionRequest(session_id=session_id, clear_metadata=True),
    )
    assert dict(cleared.session.metadata) == {}

    missing = str(uuid.uuid4())
    with pytest.raises(grpc.aio.AioRpcError) as del_err:
        await stub.DeleteSession(pb.DeleteSessionRequest(session_id=missing))
    assert del_err.value.code() == grpc.StatusCode.NOT_FOUND

    with pytest.raises(grpc.aio.AioRpcError) as list_err:
        await stub.ListSessionImages(pb.ListImagesRequest(session_id=missing))
    assert list_err.value.code() == grpc.StatusCode.NOT_FOUND

    with pytest.raises(grpc.aio.AioRpcError) as dl_err:
        async for _ in stub.DownloadImage(
            pb.DownloadImageRequest(session_id=session_id, image_id=missing),
        ):
            pass
    assert dl_err.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_struct_and_abort_helpers() -> None:
    """Struct conversion and ValidationError abort mapping."""
    from google.protobuf.struct_pb2 import Struct
    from pydantic import ValidationError

    from app.grpc_codec import _struct_to_dict
    from app.grpc_server import _abort
    from app.models import PhoneInfo

    assert _struct_to_dict(None) == {}  # type: ignore[arg-type]
    assert _struct_to_dict(Struct()) == {}
    context = _FakeContext()
    try:
        PhoneInfo.model_validate({})
    except ValidationError as exc:
        with pytest.raises(RuntimeError):
            await _abort(context, exc)
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_abort_unknown_service_error() -> None:
    """Unmapped SessionServiceError subclasses become INTERNAL."""
    from app.exceptions import SessionServiceError
    from app.grpc_codec import dict_to_struct
    from app.grpc_server import _abort

    class Mystery(SessionServiceError):
        """Synthetic error used only for mapping coverage."""

    context = _FakeContext()
    with pytest.raises(RuntimeError):
        await _abort(context, Mystery("x"))
    assert context.code == grpc.StatusCode.INTERNAL
    assert dict_to_struct({}).fields == {}
    assert "k" in dict_to_struct({"k": "v"}).fields


class _FakeContext:
    """Minimal aio ServicerContext for unit mapping tests."""

    def __init__(self) -> None:
        """Track abort arguments."""
        self.code: grpc.StatusCode | None = None
        self.details: str = ""

    def invocation_metadata(self) -> tuple:
        """Return empty gRPC metadata."""
        return ()

    async def abort(self, code: grpc.StatusCode, details: str) -> None:
        """Record and raise like grpc.aio."""
        self.code = code
        self.details = details
        raise RuntimeError("aborted")
