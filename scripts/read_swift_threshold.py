#!/usr/bin/env python3
"""Fail-closed reader for Swift numeric gates (CI-022 / SWIFT-TEST-002)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSUMER = ROOT / "config" / "swift.profile.thresholds.yml"
ANALOG = ROOT / "docs" / "guardrails" / "swift" / "profile.thresholds.yml"

HIGHER_IS_STRICTER = frozenset({"statement_coverage", "doc_coverage"})
LOWER_IS_STRICTER = frozenset(
    {
        "pr_size_soft_limit_lines",
        "lint_exception_max_days",
        "max_cyclomatic_complexity",
    }
)


def parse_int_keys(path: Path) -> dict[str, int]:
    """Parse ``key: int`` lines, ignoring comments and blanks."""
    if not path.is_file():
        raise SystemExit(f"Missing {path} (CI-022 fail closed)")
    values: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key or not value:
            raise SystemExit(f"Empty key or value in {path}: {raw!r} (CI-022 fail closed)")
        try:
            values[key] = int(value)
        except ValueError as exc:
            raise SystemExit(f"Non-integer '{key}' in {path}: {value}") from exc
    if not values:
        raise SystemExit(f"No keys in {path} (CI-022 fail closed)")
    return values


def _looser_than_analog(key: str, consumer_value: int, analog_value: int) -> bool:
    """True when the consumer overlay weakens the analog gate."""
    if key in HIGHER_IS_STRICTER:
        return consumer_value < analog_value
    if key in LOWER_IS_STRICTER:
        return consumer_value > analog_value
    return consumer_value != analog_value


def load_thresholds() -> dict[str, int]:
    """Load consumer copy and optionally assert analog overlay rules."""
    consumer = parse_int_keys(CONSUMER)
    if ANALOG.is_file():
        analog = parse_int_keys(ANALOG)
        for key, analog_value in analog.items():
            consumer_value = consumer.get(key)
            if consumer_value is None:
                raise SystemExit(
                    f"{CONSUMER.name} missing analog key '{key}' ({ANALOG}). "
                    "Update the consumer copy when bumping docs/guardrails.",
                )
            if _looser_than_analog(key, consumer_value, analog_value):
                raise SystemExit(
                    f"{CONSUMER.name} {key}={consumer_value} is looser than analog "
                    f"{analog_value} ({ANALOG}). Being stricter is allowed; loosening "
                    "requires a recorded deviation.",
                )
    return consumer


def read_threshold(key: str) -> int:
    """Return one integer threshold or exit."""
    values = load_thresholds()
    if key not in values:
        raise SystemExit(f"Missing key '{key}' in {CONSUMER} (CI-022 fail closed)")
    return values[key]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <key>")
    print(read_threshold(sys.argv[1]))
