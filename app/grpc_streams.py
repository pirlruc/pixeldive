"""Client-stream assembly for gRPC image uploads."""

from app.grpc_batch import assemble_batch
from app.grpc_single import assemble_single

__all__ = ["assemble_batch", "assemble_single"]
