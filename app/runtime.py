"""Process bootstrap: database, dual servers, sweeper, and shutdown."""

from __future__ import annotations

import asyncio
import logging

import uvicorn

from app.api import create_app
from app.config import Settings, get_settings
from app.database import create_engine, init_db, session_factory
from app.grpc_server import start_grpc_server
from app.lifecycle import close_storage, orphan_sweep_loop, serve_until_stopped
from app.metrics import Metrics
from app.migrate import upgrade_head
from app.observability import configure_logging
from app.service import SessionService
from app.storage import build_storage

logger = logging.getLogger("pixeldive")

_PRODUCTION = frozenset({"prod", "production"})


def is_production(settings: Settings) -> bool:
    """True when ``ENVIRONMENT`` names a production profile."""
    return settings.environment.strip().lower() in _PRODUCTION


def validate_auth_settings(settings: Settings) -> None:
    """Fail fast when auth is required without tokens, or production is open."""
    if is_production(settings):
        if not settings.auth_required:
            msg = "ENVIRONMENT=production requires AUTH_REQUIRED=true"
            raise RuntimeError(msg)
        if settings.grpc_insecure:
            msg = "ENVIRONMENT=production requires GRPC_INSECURE=false"
            raise RuntimeError(msg)
    if settings.auth_required and not settings.api_key_map():
        msg = "AUTH_REQUIRED is true but API_KEYS is empty"
        raise RuntimeError(msg)


async def run(settings: Settings | None = None) -> None:
    """Initialize the database and serve REST + gRPC until interrupted."""
    settings = settings or get_settings()
    configure_logging(json_logs=settings.log_json)
    validate_auth_settings(settings)
    if not settings.auth_required:
        logger.warning("AUTH_REQUIRED is false; sessions are unauthenticated")
    engine = create_engine(settings)
    if settings.auto_create_tables:
        await init_db(engine)
    else:
        await upgrade_head(settings.database_url)
    service, grpc_server, http = await _bind(settings, engine)
    stop = asyncio.Event()
    sweeper = start_sweeper(service, settings.orphan_sweep_interval_seconds, stop)
    try:
        await serve_until_stopped(http, grpc_server, stop)
    finally:
        stop.set()
        await stop_sweeper(sweeper)
        await close_storage(service._storage)
        await engine.dispose()


async def _bind(settings: Settings, engine: object) -> tuple[SessionService, object, object]:
    """Construct SessionService plus the HTTP and gRPC servers."""
    factory = session_factory(engine)  # type: ignore[arg-type]
    metrics = Metrics()
    service = SessionService(factory, build_storage(settings), settings, metrics)
    grpc_server, _bound_port = await start_grpc_server(
        service,
        settings.grpc_host,
        settings.grpc_port,
    )
    app = create_app(service, metrics)
    http = uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.http_host,
            port=settings.http_port,
            log_level="info",
            lifespan="on",
        ),
    )
    logger.info(
        "listening http://%s:%s grpc://%s:%s",
        settings.http_host,
        settings.http_port,
        settings.grpc_host,
        settings.grpc_port,
    )
    return service, grpc_server, http


def start_sweeper(
    service: SessionService,
    interval: float,
    stop: asyncio.Event,
) -> asyncio.Task[None] | None:
    """Schedule the orphan sweeper when the interval is positive (DATA-004)."""
    if interval <= 0:
        return None
    return asyncio.create_task(orphan_sweep_loop(service, interval, stop), name="pixeldive-sweep")


async def stop_sweeper(task: asyncio.Task[None] | None) -> None:
    """Cancel the background sweeper if it was started."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return
