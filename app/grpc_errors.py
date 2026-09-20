"""gRPC status mapping for SessionServiceError subclasses."""

from typing import NoReturn

import grpc
from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.error_map import grpc_status


async def abort_rpc(context: ServicerContext, exc: BaseException) -> NoReturn:
    """Abort the RPC with the mapped status code."""
    if isinstance(exc, ValidationError):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
    else:
        await context.abort(grpc_status(exc), str(exc))
    raise RuntimeError("grpc abort returned")  # pragma: no cover
