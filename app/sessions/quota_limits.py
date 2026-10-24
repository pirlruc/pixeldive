"""Shared quota ceilings passed to every backend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuotaLimits:
    """Rate window and byte caps. Zero means that cap is off."""

    requests_per_window: int
    window_seconds: float
    tenant_max_bytes: int
    session_max_bytes: int
