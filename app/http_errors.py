"""HTTP status mapping for SessionServiceError subclasses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    BatchLimitError,
    EmptyImageError,
    ForbiddenError,
    ImageNotFoundError,
    ImageTooLargeError,
    InvalidIdError,
    InvalidMetadataError,
    InvalidStatusError,
    SessionNotFoundError,
    SessionServiceError,
    UnauthenticatedError,
    UnsupportedContentTypeError,
)

ERROR_STATUS: dict[type[SessionServiceError], int] = {
    SessionNotFoundError: 404,
    ImageNotFoundError: 404,
    InvalidStatusError: 422,
    InvalidIdError: 422,
    InvalidMetadataError: 422,
    UnsupportedContentTypeError: 422,
    EmptyImageError: 422,
    BatchLimitError: 422,
    ImageTooLargeError: 413,
    UnauthenticatedError: 401,
    ForbiddenError: 403,
}


def register_error_handlers(app: FastAPI) -> None:
    """Map SessionServiceError subclasses to HTTP status codes."""

    async def handle_service_error(_request: Request, exc: SessionServiceError) -> JSONResponse:
        """Serialize a domain error as ``{"detail": ...}``."""
        status = ERROR_STATUS[type(exc)]
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    for error_type in ERROR_STATUS:
        app.add_exception_handler(error_type, handle_service_error)  # type: ignore[arg-type]
