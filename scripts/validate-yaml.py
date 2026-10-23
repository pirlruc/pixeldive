#!/usr/bin/env python3
"""Parse YAML files and fail if an expected path is missing.

Usage:
  python3 validate-yaml.py [--root DIR] [--glob PATTERN] FILE [FILE ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Base directory")
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        dest="globs",
        help="Glob relative to --root (repeatable); must match at least one file",
    )
    parser.add_argument("files", nargs="*", help="Expected files relative to --root")
    return parser.parse_args(argv)


def _existing_files(root: Path, files: list[str]) -> tuple[list[Path], list[str]]:
    """Return found files and missing relative paths."""
    found: list[Path] = []
    missing: list[str] = []
    for rel in files:
        path = root / rel
        if path.is_file():
            found.append(path)
        else:
            missing.append(rel)
    return found, missing


def _glob_files(root: Path, globs: list[str]) -> tuple[list[Path], list[str]]:
    """Return glob matches and patterns that matched nothing."""
    found: list[Path] = []
    empty: list[str] = []
    for pattern in globs:
        matched = sorted(p for p in root.glob(pattern) if p.is_file())
        if not matched:
            empty.append(pattern)
        found.extend(matched)
    return found, empty


def collect_paths(root: Path, files: list[str], globs: list[str]) -> list[Path]:
    """Resolve expected files and glob matches; missing expected files raise."""
    paths, missing = _existing_files(root, files)
    globbed, empty_globs = _glob_files(root, globs)
    paths.extend(globbed)
    if missing:
        raise FileNotFoundError("missing YAML file(s): " + ", ".join(missing))
    if empty_globs:
        raise FileNotFoundError("glob matched nothing: " + ", ".join(empty_globs))
    if not paths:
        raise FileNotFoundError("no YAML files to parse")
    return paths


def parse_files(paths: list[Path]) -> None:
    """Parse each YAML file with yaml.safe_load."""
    for path in paths:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        print("ok", path)


def main(argv: list[str] | None = None) -> int:
    """Parse YAML files; return 0 on success, 1 on error."""
    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    try:
        paths = collect_paths(root, args.files, args.globs)
        parse_files(paths)
    except (FileNotFoundError, yaml.YAMLError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
