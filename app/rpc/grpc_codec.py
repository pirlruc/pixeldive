"""Protobuf mapping helpers for the gRPC transport."""

import uuid
from typing import Any, Protocol, cast

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Struct
from google.protobuf.timestamp_pb2 import Timestamp
from grpc.aio import ServicerContext

from app.exceptions import InvalidIdError
from app.models import (
    CameraCapabilities,
    CameraInfo,
    PhoneCapabilities,
    PhoneInfo,
    Session,
    SessionImage,
)
from app.pb import session_service_pb2 as pb

_PROTO_JSON = {
    "preserving_proto_field_name": True,
    "always_print_fields_with_no_presence": True,
}


class _Validatable(Protocol):
    """Pydantic model with ``model_validate`` (device payloads)."""

    @classmethod
    def model_validate(cls, obj: Any) -> Any:
        """Rehydrate from a dict."""
        ...


def as_uuid(value: str, context: ServicerContext) -> uuid.UUID:
    """Parse a UUID or raise InvalidIdError."""
    del context
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise InvalidIdError(f"invalid uuid: {value}") from exc


def _from_pb[T: _Validatable](model_cls: type[T], message: object) -> T:
    """Validate a protobuf message as a Pydantic device model."""
    return cast(T, model_cls.model_validate(MessageToDict(message, **_PROTO_JSON)))


def phone_info(message: pb.PhoneInfo) -> PhoneInfo:
    """Map protobuf PhoneInfo to the SQLModel schema."""
    return _from_pb(PhoneInfo, message)


def phone_caps(message: pb.PhoneCapabilities) -> PhoneCapabilities:
    """Map protobuf PhoneCapabilities to the SQLModel schema."""
    return _from_pb(PhoneCapabilities, message)


def camera_caps(message: pb.CameraCapabilities) -> CameraCapabilities:
    """Map protobuf CameraCapabilities, including the repeated cameras list."""
    cameras = [_from_pb(CameraInfo, item) for item in message.cameras]
    return CameraCapabilities(camera_count=message.camera_count, cameras=cameras)


def struct_to_dict(message: Struct) -> dict[str, Any]:
    """Convert a protobuf Struct to a plain dict."""
    if message is None or not message.fields:
        return {}
    return dict(MessageToDict(message))


def dict_to_struct(data: dict[str, Any]) -> Struct:
    """Convert a dict to protobuf Struct."""
    struct = Struct()
    if data:
        ParseDict(data, struct)
    return struct


def timestamp(value: Any) -> Timestamp:
    """Convert a datetime to protobuf Timestamp."""
    stamp = Timestamp()
    stamp.FromDatetime(value)
    return stamp


def session_to_pb(session: Session) -> pb.Session:
    """Map a Session row to protobuf."""
    return pb.Session(
        id=str(session.id),
        session_name=session.session_name,
        status=session.status,
        created_at=timestamp(session.created_at),
        updated_at=timestamp(session.updated_at),
        phone_info=pb.PhoneInfo(**session.phone_info.model_dump()),
        phone_capabilities=pb.PhoneCapabilities(**session.phone_capabilities.model_dump()),
        camera_capabilities=pb.CameraCapabilities(
            camera_count=session.camera_capabilities.camera_count,
            cameras=[
                pb.CameraInfo(**item.model_dump()) for item in session.camera_capabilities.cameras
            ],
        ),
        metadata=dict_to_struct(session.extra_metadata),
    )


def image_to_pb(image: SessionImage) -> pb.SessionImage:
    """Map a SessionImage row to protobuf."""
    return pb.SessionImage(
        id=str(image.id),
        session_id=str(image.session_id),
        filename=image.filename,
        content_type=image.content_type,
        size_bytes=image.size_bytes,
        uploaded_at=timestamp(image.uploaded_at),
        metadata=dict_to_struct(image.extra_metadata),
    )


# Historical private names used by tests and grpc_streams during the split.
_as_uuid = as_uuid
_phone_info = phone_info
_phone_caps = phone_caps
_camera_caps = camera_caps
_struct_to_dict = struct_to_dict
_dict_to_struct = dict_to_struct
_timestamp = timestamp
_session_to_pb = session_to_pb
_image_to_pb = image_to_pb
