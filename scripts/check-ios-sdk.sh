#!/usr/bin/env bash
# Local / CI parity for the Foundation iOS SDK package (CI-008, SWIFT-TEST-001).
# SwiftUI demo stays on macOS + Xcode (SWIFT-ENV-001).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=python-env.sh
source "$ROOT/scripts/python-env.sh"

STMT="$("$PYTHON" "$ROOT/scripts/read_swift_threshold.py" statement_coverage)"
DOC="$("$PYTHON" "$ROOT/scripts/read_swift_threshold.py" doc_coverage)"
MAX_CC="$("$PYTHON" "$ROOT/scripts/read_swift_threshold.py" max_cyclomatic_complexity)"

if ! command -v swift >/dev/null 2>&1; then
  echo "swift not on PATH (SWIFT-LANG-002 / SWIFT-ENV-001)" >&2
  if [[ "${PIXELDIVE_REQUIRE_SWIFT:-}" == "1" ]]; then
    exit 1
  fi
  echo "skipping swift test; set PIXELDIVE_REQUIRE_SWIFT=1 to fail closed"
  echo "ios-sdk skipped (statement_coverage=${STMT} doc_coverage=${DOC} max_cc=${MAX_CC})"
  exit 0
fi

echo "swift gates: statement_coverage=${STMT} doc_coverage=${DOC} max_cc=${MAX_CC}"
swift --version
swift test --package-path "$ROOT/ios"
echo "ios-sdk ok"
