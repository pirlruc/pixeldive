"""Map REST-shaped session dicts onto gRPC CreateSessionRequest."""

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
