#!/usr/bin/env python3
"""Fail closed if llvm-cov line coverage is below SWIFT-TEST-002."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ios"


def parse_line_cover(report: str) -> float:
    """Return the llvm-cov TOTAL lines-cover percentage."""
    for line in report.splitlines():
        stripped = line.strip()
        if not stripped.startswith("TOTAL"):
            continue
        percents = [token[:-1] for token in stripped.split() if token.endswith("%")]
        if not percents:
            raise SystemExit("llvm-cov TOTAL line has no percents (CI-022 fail closed)")
        return float(percents[-1])
    raise SystemExit("llvm-cov report has no TOTAL line (CI-022 fail closed)")


def prepend_llvm_cov_dir() -> None:
    """Put llvm-cov next to swift on PATH; argv stays the literal name."""
    if shutil.which("xcrun") or shutil.which("llvm-cov"):
        return
    swift = shutil.which("swift")
    if not swift:
        raise SystemExit("llvm-cov not found (SWIFT-TEST-002)")
    swift_path = Path(swift).resolve()
    candidates: list[Path] = [swift_path.parent / "llvm-cov"]
    for parent in swift_path.parents:
        candidates.append(parent / "bin" / "llvm-cov")
        candidates.append(parent / "usr" / "bin" / "llvm-cov")
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            os.environ["PATH"] = str(candidate.parent) + os.pathsep + os.environ.get("PATH", "")
            return
    raise SystemExit("llvm-cov not found (SWIFT-TEST-002)")


def find_profdata(package: Path) -> Path:
    """Return the coverage profile produced by ``swift test --enable-code-coverage``."""
    matches = sorted(package.glob("**/*.profdata"))
    if not matches:
        raise SystemExit(f"no .profdata under {package} (SWIFT-TEST-002)")
    return matches[-1]


def find_test_binary(package: Path) -> Path:
    """Return the XCTest bundle or Linux test executable."""
    mac_bins = sorted(package.glob("**/*.xctest/Contents/MacOS/*"))
    files = [path for path in mac_bins if path.is_file()]
    if files:
        return files[-1]
    linux_bins = sorted(package.glob("**/*PackageTests.xctest"))
    files = [path for path in linux_bins if path.is_file()]
    if files:
        return files[-1]
    raise SystemExit(f"no test binary under {package} (SWIFT-TEST-002)")


def run_llvm_cov(binary: Path, profile: Path) -> str:
    """Run llvm-cov with a literal argv0 (no PATH or CLI paths in the argv list)."""
    prepend_llvm_cov_dir()
    profile_flag = f"-instr-profile={profile}"
    ignore = "-ignore-filename-regex=Tests|checkouts|\\.build"
    binary_arg = str(binary)
    if shutil.which("xcrun"):
        result = subprocess.run(
            [
                "xcrun",
                "llvm-cov",
                "report",
                binary_arg,
                profile_flag,
                ignore,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            [
                "llvm-cov",
                "report",
                binary_arg,
                profile_flag,
                ignore,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"llvm-cov failed ({result.returncode})")
    return result.stdout


def main() -> None:
    """Parse args, run llvm-cov, and fail closed below the threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=int, required=True)
    parser.add_argument("--report-file", type=Path, default=None)
    args = parser.parse_args()
    if args.report_file is not None:
        report = args.report_file.read_text(encoding="utf-8")
    else:
        report = run_llvm_cov(find_test_binary(PACKAGE), find_profdata(PACKAGE))
        sys.stdout.write(report)
    cover = parse_line_cover(report)
    print(f"swift line coverage={cover} threshold={args.threshold}")
    if cover + 1e-9 < float(args.threshold):
        raise SystemExit(
            f"SWIFT-TEST-002 line coverage {cover} < {args.threshold} (CI-022 fail closed)"
        )


if __name__ == "__main__":
    main()
