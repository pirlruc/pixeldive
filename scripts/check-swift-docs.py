#!/usr/bin/env python3
"""Fail closed if public Swift API doc coverage is below SWIFT-DOC-001."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECL = re.compile(
    r"^\s*public\s+(?:(?:final|static|indirect|nonisolated)\s+)*"
    r"(?:struct|class|enum|actor|protocol|func|typealias)\b"
)
SKIP = re.compile(r"^\s*public\s+(?:init|func encode\(to|var |let )")


def public_doc_ratio(sources: Path) -> tuple[int, int]:
    """Return (documented, total) public type/function declarations."""
    documented = 0
    total = 0
    for path in sorted(sources.rglob("*.swift")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if SKIP.search(line) or not DECL.search(line):
                continue
            total += 1
            prior = next(
                (item.strip() for item in reversed(lines[:index]) if item.strip()),
                "",
            )
            if prior.startswith("///"):
                documented += 1
    return documented, total


def main() -> None:
    """Scan ``ios/Sources`` and fail closed below the threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "ios" / "Sources")
    parser.add_argument("--threshold", type=int, required=True)
    args = parser.parse_args()
    documented, total = public_doc_ratio(args.sources)
    if total == 0:
        raise SystemExit("no public Swift declarations (SWIFT-DOC-001 fail closed)")
    percent = 100.0 * documented / total
    print(f"swift doc coverage={percent:.1f}% ({documented}/{total}) threshold={args.threshold}")
    if percent + 1e-9 < float(args.threshold):
        raise SystemExit(
            f"SWIFT-DOC-001 doc coverage {percent:.1f} < {args.threshold} (CI-022 fail closed)"
        )


if __name__ == "__main__":
    main()
