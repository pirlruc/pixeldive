"""FastAPI REST transport for SessionService (API-001)."""

from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, FastAPI, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.metrics import Metrics
from app.models import Session, SessionCreate, SessionPage, SessionRead, SessionUpdate
from app.observability import ObservabilityMiddleware
from app.rest.api_deps import PrincipalDep, ServiceDep
from app.rest.api_images import image_router
from app.rest.http_errors import register_error_handlers
from app.sessions.service import SessionService

session_router = APIRouter(prefix="/api/v1")


def _bearer_matches(header: str, expected: str) -> bool:
    """True when ``header`` is exactly ``Bearer`` plus the configured token."""
    candidate = f"Bearer {expected}"
    if len(header) != len(candidate):
        return False
    return hmac.compare_digest(header, candidate)


def create_app(service: SessionService, metrics: Metrics | None = None) -> FastAPI:
    """Build a FastAPI app bound to a SessionService instance."""
    shared_metrics = metrics or service._metrics
    app = FastAPI(title="pixeldive session service", version="0.1.0")
    app.state.service = service
    app.state.metrics = shared_metrics
    app.add_middleware(ObservabilityMiddleware, metrics=shared_metrics)
    app.include_router(session_router)
    app.include_router(image_router)
    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe for process-up checks."""
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    async def ready() -> Response:
        """Readiness probe that fails when the database cannot be reached."""
        try:
            await service.ping_db()
        except Exception:  # noqa: BLE001 — any DB failure is not-ready
            return Response(
                content='{"status":"not_ready"}',
                status_code=503,
                media_type="application/json",
            )
        return Response(content='{"status":"ok"}', media_type="application/json")

    @app.get("/metrics", tags=["health"])
    async def metrics_endpoint(request: Request) -> PlainTextResponse:
        """Prometheus text exposition of request, error, and upload counters."""
        expected = service._settings.metrics_bearer_token
        if expected and not _bearer_matches(request.headers.get("authorization", ""), expected):
            return PlainTextResponse("unauthorized", status_code=401)
        return PlainTextResponse(shared_metrics.render(), media_type="text/plain; version=0.0.4")

    return app


@session_router.post("/sessions", status_code=201, response_model=SessionRead)
async def create_session(
    payload: SessionCreate,
    service: ServiceDep,
    principal: PrincipalDep,
) -> Session:
    """Create a session with Android device and camera JSON."""
    return await service.create_session(payload, principal)


@session_router.get("/sessions", response_model=SessionPage)
async def list_sessions(
    service: ServiceDep,
    principal: PrincipalDep,
    limit: int = Query(default=50, ge=1),
    cursor: str | None = None,
) -> SessionPage:
    """List sessions newest-first with an opaque cursor."""
    page = await service.list_sessions(limit=limit, cursor=cursor, principal=principal)
    items = [SessionRead.model_validate(item) for item in page.items]
    return SessionPage(items=items, next_cursor=page.next_cursor)


@session_router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
) -> Session:
    """Return session metadata and device specifications."""
    return await service.get_session(session_id, principal)


@session_router.put("/sessions/{session_id}", response_model=SessionRead)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    service: ServiceDep,
    principal: PrincipalDep,
) -> Session:
    """Update session status or associated metadata (replace or merge)."""
    return await service.update_session(session_id, payload, principal)


@session_router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    service: ServiceDep,
    principal: PrincipalDep,
) -> Response:
    """Delete a session, cascading image rows and unreferenced blobs."""
    await service.delete_session(session_id, principal)
    return Response(status_code=204)
