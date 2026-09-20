#!/usr/bin/env bash
# Local / CI parity for the Foundation iOS SDK package (CI-008, SWIFT-TEST-001).
# SwiftUI demo stays on macOS + Xcode (SWIFT-ENV-001). Coverage and docs fail closed.
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
"$PYTHON" "$ROOT/scripts/check-swift-docs.py" --threshold "$DOC"
swift test --package-path "$ROOT/ios" --enable-code-coverage
"$PYTHON" "$ROOT/scripts/check-swift-coverage.py" --package "$ROOT/ios" --threshold "$STMT"

SWIFTLINT=""
if command -v swiftlint >/dev/null 2>&1; then
  SWIFTLINT="$(command -v swiftlint)"
elif [[ "${PIXELDIVE_REQUIRE_SWIFT:-}" == "1" ]]; then
  SWIFTLINT="$(bash "$ROOT/scripts/install-swiftlint.sh")"
fi
if [[ -n "$SWIFTLINT" ]]; then
  echo "SwiftLint (SWIFT-LINT-001)"
  (cd "$ROOT/ios" && "$SWIFTLINT" lint --strict --config "$ROOT/ios/.swiftlint.yml")
fi

if command -v xcodebuild >/dev/null 2>&1; then
  echo "xcodebuild (SWIFT-LANG-002)"
  (
    cd "$ROOT/ios"
    xcodebuild -scheme PixeldiveSDK -destination 'platform=macOS' \
      CODE_SIGNING_ALLOWED=NO -quiet build
  )
fi
echo "ios-sdk ok"
