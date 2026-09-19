"""Client metadata JSON and the public ``metadata`` key alias (DATA-001)."""

import json
from typing import Any

from app.exceptions import InvalidMetadataError


def promote_metadata(data: Any) -> Any:
    """Accept client key ``metadata`` as ``extra_metadata`` (DATA-001)."""
    if isinstance(data, dict) and "metadata" in data and "extra_metadata" not in data:
        promoted = dict(data)
        promoted["extra_metadata"] = promoted.pop("metadata")
        return promoted
    return data


def parse_metadata_json(raw: str | None) -> dict:
    """Parse an optional JSON object used by REST form fields and gRPC chunks."""
    if raw is None or raw.strip() == "":
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidMetadataError("metadata must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise InvalidMetadataError("metadata must be a JSON object")
    return parsed
