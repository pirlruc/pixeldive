"""Dual-server lifetime: coordinated stop, storage close, orphan sweep."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from app.sessions.service import SessionService

logger = logging.getLogger("pixeldive")


async def close_storage(storage: object) -> None:
    """Await ``aclose`` when the backend exposes it (OPS-002)."""
    closer = getattr(storage, "aclose", None)
    if closer is not None:
        await closer()


async def orphan_sweep_loop(
    service: SessionService,
    interval_seconds: float,
    stop: asyncio.Event,
) -> None:
    """Run ``sweep_orphans`` on an interval until ``stop`` is set (DATA-004)."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
            return
        except TimeoutError:
            await _sweep_once(service)


async def _sweep_once(service: SessionService) -> None:
    """Sweep orphans and log failures without crashing the process."""
    try:
        removed = await service.sweep_orphans()
    except Exception:
        logger.exception("orphan sweep failed")
        return
    if removed:
        logger.info("orphan sweep deleted %s blobs", removed)


def install_stop_signals(http: Any, stop: asyncio.Event) -> None:
    """Stop HTTP and gRPC together on SIGTERM/SIGINT when the loop allows it."""

    def request_stop() -> None:
        """Mark both servers as draining."""
        http.should_exit = True
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, request_stop)
        except (NotImplementedError, RuntimeError):
            continue


async def serve_until_stopped(http: Any, grpc_server: Any, stop: asyncio.Event) -> None:
    """Run HTTP and gRPC until either exits or ``stop`` is set."""
    install_stop_signals(http, stop)
    http_task = asyncio.create_task(http.serve(), name="pixeldive-http")
    grpc_wait = asyncio.create_task(grpc_server.wait_for_termination(), name="pixeldive-grpc")
    stopper = asyncio.create_task(stop.wait(), name="pixeldive-stop")
    await asyncio.wait(
        {http_task, grpc_wait, stopper},
        return_when=asyncio.FIRST_COMPLETED,
    )
    http.should_exit = True
    stop.set()
    await grpc_server.stop(grace=5)
    await http_task
    await grpc_wait
    await _ignore_cancel(stopper)


async def _ignore_cancel(task: asyncio.Task[object]) -> None:
    """Cancel ``task`` if it is still waiting and swallow CancelledError."""
    if not task.done():
        task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return
