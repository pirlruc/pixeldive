"""Demo FastAPI app that exercises pixeldive through the Python SDK."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient, HTTPStatusError
from pixeldive_sdk import GrpcClient, RestClient

from demo.clients import DemoClients
from demo.routes import register_demo_routes


def _settings() -> tuple[str, str | None, str]:
    """Read REST URL, optional token, and gRPC target from the environment."""
    return (
        os.environ.get("PIXELDIVE_BASE_URL", "http://127.0.0.1:8000"),
        os.environ.get("PIXELDIVE_TOKEN"),
        os.environ.get("PIXELDIVE_GRPC_TARGET", "127.0.0.1:50051"),
    )


def open_demo_clients() -> DemoClients:
    """Open REST plus gRPC clients for a live demo process."""
    base, token, target = _settings()
    grpc = GrpcClient(target, token=token) if target.strip() else None
    return DemoClients(RestClient(base, token=token), grpc)


def wrap_demo_client(client: RestClient | DemoClients | None) -> DemoClients | None:
    """Accept the historic RestClient test injection or a full DemoClients pair."""
    if isinstance(client, RestClient):
        return DemoClients(client)
    return client


def create_demo_app(client: RestClient | DemoClients | None = None) -> FastAPI:
    """Build the demo UI. Inject ``client`` in tests."""
    owns_client = client is None
    app = FastAPI(title="pixeldive demo", version="0.3.0", lifespan=_lifespan(owns_client))
    app.state.client = wrap_demo_client(client)
    register_demo_routes(app, _sdk_factory(app))
    app.add_exception_handler(HTTPStatusError, _upstream_handler)  # type: ignore[arg-type]
    return app


def _sdk_factory(app: FastAPI) -> Callable[[], Awaitable[DemoClients]]:
    """Build the per-request DemoClients lookup."""

    async def sdk() -> DemoClients:
        existing = getattr(app.state, "client", None)
        if isinstance(existing, DemoClients):
            return existing
        opened = open_demo_clients()
        app.state.client = opened
        return opened

    return sdk


def _lifespan(owns_client: bool) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Open SDK clients when the process did not receive one."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.client is None:
            app.state.client = open_demo_clients()
        try:
            yield
        finally:
            if owns_client:
                await app.state.client.aclose()

    return lifespan


async def _upstream_handler(_request: Request, exc: HTTPStatusError) -> JSONResponse:
    """Surface upstream HTTP errors as JSON."""
    with suppress(Exception):
        await exc.response.aread()
    return JSONResponse(status_code=exc.response.status_code, content=_error_body(exc))


def _error_body(exc: HTTPStatusError) -> dict[str, Any]:
    """Prefer JSON error payloads from the session service."""
    try:
        payload = exc.response.json()
    except Exception:  # noqa: BLE001
        return {"detail": exc.response.text}
    if isinstance(payload, dict) and "detail" in payload:
        return payload
    return {"detail": payload}


def asgi_client_for(app: object, token: str | None = None) -> RestClient:
    """Build a RestClient that talks to an in-process pixeldive ASGI app."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    http = AsyncClient(transport=transport, base_url="http://pixeldive")
    return RestClient("http://pixeldive", token=token, client=http, owns_client=True)
