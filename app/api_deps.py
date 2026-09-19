"""FastAPI dependency injection for SessionService and the caller principal."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from app.auth import Principal, authenticate
from app.service import SessionService


async def current_service(request: Request) -> SessionService:
    """Resolve the process-wide SessionService from app state."""
    return cast(SessionService, request.app.state.service)


async def current_principal(
    request: Request,
    service: SessionService = Depends(current_service),
) -> Principal | None:
    """Authenticate the caller when AUTH_REQUIRED is set."""
    return authenticate(request.headers.get("authorization"), service._settings)


PrincipalDep = Annotated[Principal | None, Depends(current_principal)]
ServiceDep = Annotated[SessionService, Depends(current_service)]
