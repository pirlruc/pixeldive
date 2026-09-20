"""Session and image RPCs for ``GrpcClient``."""

from pixeldive_sdk.grpc_images import GrpcImageCallsMixin
from pixeldive_sdk.grpc_sessions import GrpcSessionCallsMixin


class GrpcCallsMixin(GrpcSessionCallsMixin, GrpcImageCallsMixin):
    """Combined session and image RPCs used by GrpcClient."""
