"""Map protobuf SessionImage onto the REST JSON shape."""

from __future__ import annotations

from typing import Any, cast

from google.protobuf.json_format import MessageToDict

from app.pb import session_service_pb2 as pb


def session_image_json(image: pb.SessionImage) -> dict[str, Any]:
    """Map a protobuf SessionImage onto the REST JSON shape."""
    uploaded = ""
    if image.HasField("uploaded_at"):
        uploaded = image.uploaded_at.ToJsonString()
    metadata: dict[str, Any] = {}
    if image.HasField("metadata"):
        metadata = cast(dict[str, Any], MessageToDict(image.metadata))
    return {
        "id": image.id,
        "session_id": image.session_id,
        "filename": image.filename,
        "content_type": image.content_type,
        "size_bytes": int(image.size_bytes),
        "uploaded_at": uploaded,
        "metadata": metadata,
    }
