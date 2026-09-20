"""gRPC status mapping for SessionServiceError subclasses."""

from typing import NoReturn

import grpc
from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.exceptions import (
    BatchLimitError,
    EmptyImageError,
    ForbiddenError,
    ImageNotFoundError,
    ImageTooLargeError,
    InvalidIdError,
    InvalidMetadataError,
    InvalidStatusError,
    QuotaExceededError,
    SessionNotFoundError,
    SessionServiceError,
    UnauthenticatedError,
    UnsupportedContentTypeError,
)

GRPC_STATUS: dict[type[SessionServiceError], grpc.StatusCode] = {
    SessionNotFoundError: grpc.StatusCode.NOT_FOUND,
    ImageNotFoundError: grpc.StatusCode.NOT_FOUND,
    InvalidStatusError: grpc.StatusCode.INVALID_ARGUMENT,
    InvalidIdError: grpc.StatusCode.INVALID_ARGUMENT,
    InvalidMetadataError: grpc.StatusCode.INVALID_ARGUMENT,
    UnsupportedContentTypeError: grpc.StatusCode.INVALID_ARGUMENT,
    EmptyImageError: grpc.StatusCode.INVALID_ARGUMENT,
    BatchLimitError: grpc.StatusCode.INVALID_ARGUMENT,
    ImageTooLargeError: grpc.StatusCode.RESOURCE_EXHAUSTED,
    UnauthenticatedError: grpc.StatusCode.UNAUTHENTICATED,
    ForbiddenError: grpc.StatusCode.PERMISSION_DENIED,
    QuotaExceededError: grpc.StatusCode.RESOURCE_EXHAUSTED,
}


async def abort_rpc(context: ServicerContext, exc: BaseException) -> NoReturn:
    """Abort the RPC with the mapped status code."""
    if isinstance(exc, ValidationError):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
    else:
        code = GRPC_STATUS.get(type(exc), grpc.StatusCode.INTERNAL)  # type: ignore[arg-type]
        await context.abort(code, str(exc))
    raise RuntimeError("grpc abort returned")  # pragma: no cover
