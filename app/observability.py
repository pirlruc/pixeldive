"""JSON logs, request IDs, and HTTP metrics middleware (OPS-001)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import Metrics

logger = logging.getLogger("pixeldive.http")


class JsonLogFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record, including request/rpc IDs when present."""
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "rpc_id", "method", "path", "status", "elapsed_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, json_logs: bool) -> None:
    """Install a process-wide formatter on the root logger."""
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"),
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach ``X-Request-ID``, log the request, and update Metrics."""

    def __init__(self, app: object, metrics: Metrics) -> None:
        """Bind the shared metrics object."""
        super().__init__(app)  # type: ignore[arg-type]
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Wrap one ASGI HTTP call with identity and counters."""
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._metrics.observe_request(error=True)
            logger.exception("request_failed", extra={"request_id": request_id})
            raise
        error = response.status_code >= 400
        self._metrics.observe_request(error=error)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response
