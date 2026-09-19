"""Concurrent FastAPI (Uvicorn) and gRPC aio servers on one event loop."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

import uvicorn

from app.api import create_app
from app.config import Settings, get_settings
from app.database import create_engine, init_db, session_factory
from app.grpc_server import start_grpc_server
from app.metrics import Metrics
from app.migrate import upgrade_head
from app.observability import configure_logging
from app.service import SessionService
from app.storage import build_storage

logger = logging.getLogger("pixeldive")


def _validate_auth_settings(settings: Settings) -> None:
    """Fail fast when auth is required without any configured tokens."""
    if settings.auth_required and not settings.api_key_map():
        msg = "AUTH_REQUIRED is true but API_KEYS is empty"
        raise RuntimeError(msg)


async def run(settings: Settings | None = None) -> None:
    """Initialize the database and serve REST + gRPC until interrupted."""
    settings = settings or get_settings()
    configure_logging(json_logs=settings.log_json)
    _validate_auth_settings(settings)
    engine = create_engine(settings)
    if settings.auto_create_tables:
        await init_db(engine)
    else:
        await upgrade_head(settings.database_url)
    factory = session_factory(engine)
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
    try:
        await asyncio.gather(http.serve(), grpc_server.wait_for_termination())
    finally:
        await grpc_server.stop(grace=5)
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint used by Docker ENTRYPOINT and ``python main.py``."""
    del argv
    asyncio.run(run())


if __name__ == "__main__":
    main()
