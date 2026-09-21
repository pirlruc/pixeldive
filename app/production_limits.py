"""Production quota fail-closed checks (SEC-008)."""

from __future__ import annotations

from app.config import Settings

_QUOTA_FIELDS = (
    ("RATE_LIMIT_PER_MINUTE", "rate_limit_per_minute"),
    ("TENANT_MAX_UPLOAD_BYTES", "tenant_max_upload_bytes"),
    ("SESSION_MAX_UPLOAD_BYTES", "session_max_upload_bytes"),
)


def require_production_quotas(settings: Settings) -> None:
    """Require positive rate and byte caps; development may leave them at zero."""
    missing = [name for name, attr in _QUOTA_FIELDS if getattr(settings, attr) <= 0]
    if missing:
        msg = "ENVIRONMENT=production requires positive " + ", ".join(missing)
        raise RuntimeError(msg)
