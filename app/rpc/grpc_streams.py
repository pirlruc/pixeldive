"""Client-stream assembly for gRPC image uploads."""

from app.rpc.grpc_batch import assemble_batch
from app.rpc.grpc_single import assemble_single

__all__ = ["assemble_batch", "assemble_single"]
