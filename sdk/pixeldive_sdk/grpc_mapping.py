"""Map REST-shaped session dicts onto gRPC requests."""

from __future__ import annotations

from typing import Any

from app.pb import session_service_pb2 as pb


def create_session_request(body: dict[str, Any]) -> pb.CreateSessionRequest:
    """Map a REST-shaped dict onto CreateSessionRequest."""
    from google.protobuf.struct_pb2 import Struct

    info = body["phone_info"]
    caps = body["phone_capabilities"]
    cameras = body["camera_capabilities"]
    metadata = Struct()
    metadata.update(body.get("metadata") or {})
    return pb.CreateSessionRequest(
        session_name=body["session_name"],
        phone_info=pb.PhoneInfo(**info),
        phone_capabilities=pb.PhoneCapabilities(**caps),
        camera_capabilities=pb.CameraCapabilities(
            camera_count=cameras["camera_count"],
            cameras=[pb.CameraInfo(**item) for item in cameras["cameras"]],
        ),
        metadata=metadata,
    )


def update_session_request(
    session_id: str,
    payload: dict[str, Any],
    *,
    merge_metadata: bool = False,
) -> pb.UpdateSessionRequest:
    """Map a REST-shaped patch onto UpdateSessionRequest."""
    from google.protobuf.struct_pb2 import Struct

    request = pb.UpdateSessionRequest(session_id=session_id, merge_metadata=merge_metadata)
    if "session_name" in payload and payload["session_name"] is not None:
        request.session_name = str(payload["session_name"])
    if "status" in payload and payload["status"] is not None:
        request.status = str(payload["status"])
    if "metadata" in payload and payload["metadata"] is not None:
        metadata = Struct()
        metadata.update(payload["metadata"])
        request.metadata.CopyFrom(metadata)
    if payload.get("clear_metadata"):
        request.clear_metadata = True
    return request
