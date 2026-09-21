"""Shared gRPC principal resolution and unary try/abort wrapper."""

from collections.abc import Awaitable, Callable

from grpc.aio import ServicerContext
from pydantic import ValidationError

from app.exceptions import SessionServiceError
from app.rpc.grpc_errors import abort_rpc
from app.sessions.auth import Principal, authenticate, metadata_authorization
from app.sessions.service import SessionService


def rpc_principal(context: ServicerContext, service: SessionService) -> Principal | None:
    """Resolve the caller from gRPC metadata."""
    header = metadata_authorization(tuple(context.invocation_metadata()))
    return authenticate(header, service._settings)


async def run_unary[T](
    context: ServicerContext,
    service: SessionService,
    work: Callable[[Principal | None], Awaitable[T]],
) -> T:
    """Run an authenticated unary RPC and abort on mapped domain errors."""
    try:
        return await work(rpc_principal(context, service))
    except (SessionServiceError, ValidationError) as exc:
        await abort_rpc(context, exc)
