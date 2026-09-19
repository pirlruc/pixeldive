#!/usr/bin/env python3
"""Fail closed on High/Critical SARIF results (CI-005).

CodeQL, mobsfscan, and OSV Scanner all emit SARIF. Medium findings are
printed so they can be reduced, but they do not fail the job unless
--min-severity medium is passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RANK = {
    "note": 0,
    "low": 0,
    "info": 0,
    "warning": 1,
    "medium": 1,
    "error": 2,
    "high": 2,
    "critical": 3,
}


def cvss_to_level(score: float) -> str:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def rule_map(sarif: dict) -> dict[str, dict]:
    rules: dict[str, dict] = {}
    for run in sarif.get("runs") or []:
        driver = (run.get("tool") or {}).get("driver") or {}
        for rule in driver.get("rules") or []:
            rule_id = rule.get("id")
            if rule_id:
                rules[str(rule_id)] = rule
    return rules


def result_level(result: dict, rules: dict[str, dict]) -> str:
    props = result.get("properties") or {}
    for key in ("security-severity", "severity", "priority"):
        if key in props:
            if isinstance(props[key], str) and props[key].lower() in RANK:
                return props[key].lower()
            score = as_float(props[key])
            if score is not None:
                return cvss_to_level(score)

    rule_id = (result.get("ruleId") or "").strip()
    rule = rules.get(rule_id) or {}
    rule_props = rule.get("properties") or {}
    score = as_float(rule_props.get("security-severity"))
    if score is not None:
        return cvss_to_level(score)
    for key in ("precision", "severity", "problem.severity"):
        raw = rule_props.get(key)
        if isinstance(raw, str) and raw.lower() in RANK:
            if key == "precision":
                continue
            return raw.lower()

    tags = [str(t).lower() for t in (rule_props.get("tags") or [])]
    level = (
        result.get("level") or (rule.get("defaultConfiguration") or {}).get("level") or "warning"
    )
    level = str(level).lower()
    if level == "error" and any("security" in t for t in tags):
        return "high"
    if level in RANK:
        return (
            "critical"
            if level == "error" and "critical" in tags
            else ("high" if level == "error" else level)
        )
    return "medium"


def locations(result: dict) -> str:
    parts: list[str] = []
    for loc in result.get("locations") or []:
        phys = (loc.get("physicalLocation") or {}).get("artifactLocation") or {}
        region = (loc.get("physicalLocation") or {}).get("region") or {}
        uri = phys.get("uri") or "?"
        line = region.get("startLine")
        parts.append(f"{uri}:{line}" if line else str(uri))
    return ", ".join(parts) if parts else "(no location)"


def collect_sarif_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.sarif")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"error: SARIF path not found: {path}", file=sys.stderr)
            sys.exit(2)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="SARIF files or directories")
    parser.add_argument(
        "--min-severity",
        choices=("medium", "high", "critical"),
        default="high",
        help="Fail when any result is at least this severity (default: high)",
    )
    args = parser.parse_args()

    files = collect_sarif_files(args.paths)
    if not files:
        print("error: no SARIF files found (fail closed)", file=sys.stderr)
        return 2

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    blocking: list[str] = []
    medium: list[str] = []
    min_rank = RANK[args.min_severity]

    for file in files:
        try:
            sarif = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"error: invalid SARIF {file}: {exc}", file=sys.stderr)
            return 2
        rules = rule_map(sarif)
        for run in sarif.get("runs") or []:
            for result in run.get("results") or []:
                level = result_level(result, rules)
                bucket = level if level in counts else "medium"
                counts[bucket] += 1
                message = ((result.get("message") or {}).get("text") or "").splitlines()[0]
                rule_id = result.get("ruleId") or "?"
                line = f"{file.name} {bucket.upper()} {rule_id} {locations(result)} {message}"
                if RANK.get(level, 1) >= min_rank:
                    blocking.append(line)
                elif bucket == "medium":
                    medium.append(line)

    print(
        "SARIF summary: "
        f"critical={counts['critical']} high={counts['high']} "
        f"medium={counts['medium']} low={counts['low']} files={len(files)}"
    )
    for line in blocking:
        print(line, file=sys.stderr)
    for line in medium[:40]:
        print(line)
    extra = len(medium) - min(len(medium), 40)
    if extra > 0:
        print(f"... {extra} more medium findings")

    if blocking:
        print(
            f"error: {len(blocking)} finding(s) at or above {args.min_severity} (CI-005)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
