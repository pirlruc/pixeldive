"""Single exception → HTTP/gRPC status table used by both transports."""

from dataclasses import dataclass

import grpc

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


@dataclass(frozen=True, slots=True)
class TransportStatus:
    """Paired HTTP status and gRPC status code for one domain error."""

    http: int
    grpc: grpc.StatusCode


ERROR_STATUS: dict[type[SessionServiceError], TransportStatus] = {
    SessionNotFoundError: TransportStatus(404, grpc.StatusCode.NOT_FOUND),
    ImageNotFoundError: TransportStatus(404, grpc.StatusCode.NOT_FOUND),
    InvalidStatusError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    InvalidIdError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    InvalidMetadataError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    UnsupportedContentTypeError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    EmptyImageError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    BatchLimitError: TransportStatus(422, grpc.StatusCode.INVALID_ARGUMENT),
    ImageTooLargeError: TransportStatus(413, grpc.StatusCode.RESOURCE_EXHAUSTED),
    UnauthenticatedError: TransportStatus(401, grpc.StatusCode.UNAUTHENTICATED),
    ForbiddenError: TransportStatus(403, grpc.StatusCode.PERMISSION_DENIED),
    QuotaExceededError: TransportStatus(429, grpc.StatusCode.RESOURCE_EXHAUSTED),
}


def http_status(exc: SessionServiceError) -> int:
    """Return the HTTP status for a mapped domain error."""
    return ERROR_STATUS[type(exc)].http


def grpc_status(exc: BaseException) -> grpc.StatusCode:
    """Return the gRPC status for a mapped domain error, else INTERNAL."""
    mapped = ERROR_STATUS.get(type(exc))  # type: ignore[arg-type]
    if mapped is None:
        return grpc.StatusCode.INTERNAL
    return mapped.grpc
