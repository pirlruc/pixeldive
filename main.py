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
from app.service import SessionService
from app.storage import build_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pixeldive")


async def run(settings: Settings | None = None) -> None:
    """Initialize the database and serve REST + gRPC until interrupted."""
    settings = settings or get_settings()
    engine = create_engine(settings)
    await init_db(engine)
    factory = session_factory(engine)
    service = SessionService(factory, build_storage(settings), settings)
    grpc_server, _bound_port = await start_grpc_server(
        service,
        settings.grpc_host,
        settings.grpc_port,
    )
    app = create_app(service)
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
