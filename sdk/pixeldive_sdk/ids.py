"""Validate resource identifiers used in HTTP paths."""

from uuid import UUID


def resource_id(value: str) -> str:
    """Return a canonical UUID string, rejecting path-injection payloads."""
    return str(UUID(value))
