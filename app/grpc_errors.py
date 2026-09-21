"""gRPC status mapping for SessionServiceError subclasses."""

from collections.abc import Awaitable, Callable
from typing import NoReturn

import grpc
from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.error_map import grpc_status
from app.exceptions import EmptyImageError, ImageTooLargeError


async def abort_rpc(context: ServicerContext, exc: BaseException) -> NoReturn:
    """Abort the RPC with the mapped status code."""
    if isinstance(exc, ValidationError):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
    else:
        await context.abort(grpc_status(exc), str(exc))
    raise RuntimeError("grpc abort returned")  # pragma: no cover


async def require_session_id(
    raw: str,
    context: ServicerContext,
    cleanup: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """Abort when a chunk omitted session_id, after optional spool cleanup."""
    if raw:
        return
    if cleanup is not None:
        await cleanup()
    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id is required")
    raise RuntimeError("grpc abort returned")  # pragma: no cover


async def rethrow_ingest(
    context: ServicerContext,
    exc: BaseException,
    cleanup: Callable[[], Awaitable[None]],
) -> NoReturn:
    """Drop partial spools, abort size errors, and re-raise anything else."""
    await cleanup()
    if isinstance(exc, ImageTooLargeError | EmptyImageError):
        await abort_rpc(context, exc)
    raise exc
