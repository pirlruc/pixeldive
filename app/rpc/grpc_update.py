"""Map protobuf update flags onto SessionUpdate replace/merge/clear semantics."""

from app.models import SessionUpdate
from app.pb import session_service_pb2 as pb
from app.rpc.grpc_codec import struct_to_dict


def update_patch(request: pb.UpdateSessionRequest) -> SessionUpdate:
    """Build a SessionUpdate from protobuf presence flags."""
    incoming = struct_to_dict(request.metadata)
    merge = bool(request.HasField("merge_metadata") and request.merge_metadata)
    clear = bool(request.HasField("clear_metadata") and request.clear_metadata)
    extra: dict | None
    if clear:
        extra = {}
        merge = False
    elif merge or incoming:
        extra = incoming
    else:
        extra = None
    return SessionUpdate(
        session_name=request.session_name if request.HasField("session_name") else None,
        status=request.status if request.HasField("status") else None,  # type: ignore[arg-type]
        extra_metadata=extra,
        merge_metadata=merge,
    )
