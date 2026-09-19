"""In-process RED-style counters exported as Prometheus text (OPS-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Metrics:
    """Process-wide request, error, and upload-byte counters."""

    requests_total: int = 0
    errors_total: int = 0
    upload_bytes_total: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def observe_request(self, *, error: bool) -> None:
        """Count one HTTP or RPC completion."""
        with self._lock:
            self.requests_total += 1
            if error:
                self.errors_total += 1

    def observe_upload(self, size_bytes: int) -> None:
        """Count accepted upload bytes."""
        with self._lock:
            self.upload_bytes_total += size_bytes

    def render(self) -> str:
        """Return Prometheus 0.0.4 text exposition."""
        with self._lock:
            requests = self.requests_total
            errors = self.errors_total
            upload = self.upload_bytes_total
        return "\n".join(
            [
                "# HELP pixeldive_requests_total Completed HTTP and gRPC requests.",
                "# TYPE pixeldive_requests_total counter",
                f"pixeldive_requests_total {requests}",
                "# HELP pixeldive_errors_total Requests that failed (HTTP >=400 or RPC error).",
                "# TYPE pixeldive_errors_total counter",
                f"pixeldive_errors_total {errors}",
                "# HELP pixeldive_upload_bytes_total Accepted image payload bytes.",
                "# TYPE pixeldive_upload_bytes_total counter",
                f"pixeldive_upload_bytes_total {upload}",
                "",
            ],
        )
