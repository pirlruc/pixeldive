"""Shared REST/gRPC credential parsing (SEC-001)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.exceptions import UnauthenticatedError

if TYPE_CHECKING:
    from app.config import Settings


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller identity used for session ownership."""

    owner_id: str


def parse_api_keys(raw: str) -> dict[str, str]:
    """Parse ``API_KEYS`` as JSON ``{token: owner}`` or ``token:owner`` pairs."""
    text = raw.strip()
    if not text:
        return {}
    if text.startswith("{") or text.startswith("["):
        return _parse_json_keys(text)
    return _parse_pair_keys(text)


def _parse_json_keys(text: str) -> dict[str, str]:
    """Parse a JSON object of token → owner_id."""
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "API_KEYS JSON must be an object"
        raise ValueError(msg)
    return {str(key): str(value) for key, value in data.items()}


def _parse_pair_keys(text: str) -> dict[str, str]:
    """Parse comma-separated ``token:owner`` entries."""
    mapping: dict[str, str] = {}
    for part in text.split(","):
        item = part.strip()
        if not item:
            continue
        token, sep, owner = item.partition(":")
        token = token.strip()
        owner = owner.strip() if sep else token
        if token:
            mapping[token] = owner or token
    return mapping


def bearer_token(authorization: str | None) -> str | None:
    """Extract a Bearer token from an Authorization header value."""
    if not authorization:
        return None
    scheme, _, remainder = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = remainder.strip()
    return token or None


def authenticate(authorization: str | None, settings: Settings) -> Principal | None:
    """Return a Principal when auth is on; None when auth is disabled.

    Raises:
        UnauthenticatedError: auth is required and the token is missing/unknown.
    """
    if not settings.auth_required:
        return None
    token = bearer_token(authorization)
    keys = settings.api_key_map()
    if token is None or token not in keys:
        raise UnauthenticatedError("invalid or missing bearer token")
    return Principal(owner_id=keys[token])


def metadata_authorization(
    pairs: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> str | None:
    """Read the first authorization metadata value from a gRPC invocation."""
    for key, value in pairs:
        if key.lower() == "authorization":
            return value
    return None
