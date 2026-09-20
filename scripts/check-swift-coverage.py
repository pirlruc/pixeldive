#!/usr/bin/env python3
"""Fail closed if llvm-cov line coverage is below SWIFT-TEST-002."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def llvm_cov_cmd() -> list[str]:
    """Return the llvm-cov argv prefix (xcrun on Apple, toolchain elsewhere)."""
    xcrun = shutil.which("xcrun")
    if xcrun:
        return [xcrun, "llvm-cov"]
    direct = shutil.which("llvm-cov")
    if direct:
        return [direct]
    swift = shutil.which("swift")
    if swift:
        toolchain = Path(swift).resolve().parent.parent / "usr" / "bin" / "llvm-cov"
        if toolchain.is_file():
            return [str(toolchain)]
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


def main() -> None:
    """Parse args, run llvm-cov, and fail closed below the threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "ios")
    parser.add_argument("--threshold", type=int, required=True)
    parser.add_argument("--report-file", type=Path, default=None)
    args = parser.parse_args()
    if args.report_file is not None:
        report = args.report_file.read_text(encoding="utf-8")
    else:
        cmd = [
            *llvm_cov_cmd(),
            "report",
            str(find_test_binary(args.package)),
            f"-instr-profile={find_profdata(args.package)}",
            "-ignore-filename-regex=Tests|checkouts|\\.build",
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            raise SystemExit(f"llvm-cov failed ({result.returncode})")
        report = result.stdout
        sys.stdout.write(report)
    cover = parse_line_cover(report)
    print(f"swift line coverage={cover} threshold={args.threshold}")
    if cover + 1e-9 < float(args.threshold):
        raise SystemExit(
            f"SWIFT-TEST-002 line coverage {cover} < {args.threshold} (CI-022 fail closed)"
        )


if __name__ == "__main__":
    main()
