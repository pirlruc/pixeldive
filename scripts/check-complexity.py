#!/usr/bin/env python3
"""Fail closed if radon CC / MI disagree with the Python profile (PY-CPLX-*)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from read_python_threshold import read_threshold  # noqa: E402

TARGETS = ["app", "main.py"]


def _run(args: list[str]) -> str:
    """Run a command and return stdout."""
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return result.stdout


def _cc_blocks() -> list[dict]:
    """Parse radon cc JSON into a flat list of blocks."""
    raw = json.loads(
        _run(
            [
                sys.executable,
                "-m",
                "radon",
                "cc",
                "-j",
                "-s",
                "-e",
                "app/pb/*",
                *TARGETS,
            ],
        ),
    )
    blocks: list[dict] = []
    for file_blocks in raw.values():
        blocks.extend(file_blocks)
    return blocks


def _mi_values() -> list[float]:
    """Parse radon mi JSON into maintainability scores."""
    raw = json.loads(
        _run([sys.executable, "-m", "radon", "mi", "-j", "-e", "app/pb/*", *TARGETS]),
    )
    scores: list[float] = []
    for item in raw.values():
        scores.append(float(item["mi"]))
    return scores


def main() -> int:
    """Compare radon output to profile thresholds."""
    max_cc = read_threshold("max_cyclomatic_complexity")
    avg_cc = read_threshold("avg_cyclomatic_complexity")
    min_mi = read_threshold("min_maintainability_index")
    avg_mi = read_threshold("avg_maintainability_index")

    blocks = [b for b in _cc_blocks() if b.get("type") in {"function", "method", "closure"}]
    complexities = [int(b["complexity"]) for b in blocks]
    if not complexities:
        print("radon cc: no blocks", file=sys.stderr)
        return 1
    worst = max(complexities)
    mean = sum(complexities) / len(complexities)
    if worst > max_cc:
        offenders = [b for b in blocks if int(b["complexity"]) > max_cc]
        print(f"PY-CPLX-001 max CC {worst} > {max_cc}: {offenders[:5]}", file=sys.stderr)
        return 1
    if mean > avg_cc:
        print(f"PY-CPLX-001 avg CC {mean:.2f} > {avg_cc}", file=sys.stderr)
        return 1

    scores = _mi_values()
    lowest = min(scores)
    mean_mi = sum(scores) / len(scores)
    if lowest < min_mi:
        print(f"PY-CPLX-002 min MI {lowest:.2f} < {min_mi}", file=sys.stderr)
        return 1
    if mean_mi < avg_mi:
        print(f"PY-CPLX-002 avg MI {mean_mi:.2f} < {avg_mi}", file=sys.stderr)
        return 1
    print(
        f"radon gates: max CC {worst} avg CC {mean:.2f} min MI {lowest:.2f} avg MI {mean_mi:.2f}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
