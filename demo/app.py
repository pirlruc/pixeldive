"""Demo FastAPI app that exercises pixeldive through the Python SDK."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient, HTTPStatusError
from pixeldive_sdk import RestClient

from demo.routes import register_demo_routes


def _settings() -> tuple[str, str | None]:
    """Read demo target URL and optional bearer token from the environment."""
    return (
        os.environ.get("PIXELDIVE_BASE_URL", "http://127.0.0.1:8000"),
        os.environ.get("PIXELDIVE_TOKEN"),
    )


def create_demo_app(client: RestClient | None = None) -> FastAPI:
    """Build the demo UI. Inject ``client`` in tests."""
    owns_client = client is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Open an SDK client when the process did not receive one."""
        if app.state.client is None:
            base, token = _settings()
            app.state.client = RestClient(base, token=token)
        try:
            yield
        finally:
            if owns_client:
                await app.state.client.aclose()

    app = FastAPI(title="pixeldive demo", version="0.2.0", lifespan=lifespan)
    app.state.client = client

    async def sdk() -> RestClient:
        existing = getattr(app.state, "client", None)
        if isinstance(existing, RestClient):
            return existing
        base, token = _settings()
        opened = RestClient(base, token=token)
        app.state.client = opened
        return opened

    register_demo_routes(app, sdk)

    @app.exception_handler(HTTPStatusError)
    async def upstream_error(_request: object, exc: HTTPStatusError) -> JSONResponse:
        """Surface upstream HTTP errors as JSON."""
        return JSONResponse(status_code=exc.response.status_code, content=_error_body(exc))

    return app


def _error_body(exc: HTTPStatusError) -> dict[str, Any]:
    """Prefer JSON error payloads from the session service."""
    try:
        return {"detail": exc.response.json()}
    except Exception:  # noqa: BLE001
        return {"detail": exc.response.text}


def asgi_client_for(app: object, token: str | None = None) -> RestClient:
    """Build a RestClient that talks to an in-process pixeldive ASGI app."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    http = AsyncClient(transport=transport, base_url="http://pixeldive")
    return RestClient("http://pixeldive", token=token, client=http)
