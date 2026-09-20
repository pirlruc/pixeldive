"""HTTP status mapping for SessionServiceError subclasses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.error_map import ERROR_STATUS, http_status
from app.exceptions import SessionServiceError


def register_error_handlers(app: FastAPI) -> None:
    """Map SessionServiceError subclasses to HTTP status codes."""

    async def handle_service_error(_request: Request, exc: SessionServiceError) -> JSONResponse:
        """Serialize a domain error as ``{"detail": ...}``."""
        return JSONResponse(status_code=http_status(exc), content={"detail": str(exc)})

    for error_type in ERROR_STATUS:
        app.add_exception_handler(error_type, handle_service_error)  # type: ignore[arg-type]
