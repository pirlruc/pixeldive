#!/usr/bin/env bash
# Local / CI parity for the Kotlin JVM Android SDK (CI-008, KT-TEST-001).
# Compose demo stays host-only (KT-ENV-001). Coverage and lint fail closed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=python-env.sh
source "$ROOT/scripts/python-env.sh"

STMT="$("$PYTHON" "$ROOT/scripts/read_kotlin_threshold.py" statement_coverage)"
BRANCH="$("$PYTHON" "$ROOT/scripts/read_kotlin_threshold.py" branch_coverage)"
MAX_CC="$("$PYTHON" "$ROOT/scripts/read_kotlin_threshold.py" max_cyclomatic_complexity)"

if ! command -v java >/dev/null 2>&1; then
  echo "java not on PATH (KT-BUILD-001 / KT-ENV-001)" >&2
  if [[ "${PIXELDIVE_REQUIRE_JAVA:-}" == "1" ]]; then
    exit 1
  fi
  echo "skipping gradle test; set PIXELDIVE_REQUIRE_JAVA=1 to fail closed"
  echo "android-sdk skipped (statement_coverage=${STMT} branch_coverage=${BRANCH} max_cc=${MAX_CC})"
  exit 0
fi

echo "kotlin gates: statement_coverage=${STMT} branch_coverage=${BRANCH} max_cc=${MAX_CC}"
java -version
bash "$ROOT/android/gradlew" -p "$ROOT/android" --no-daemon \
  -Ppixeldive.statementCoverage="$STMT" \
  -Ppixeldive.branchCoverage="$BRANCH" \
  -Ppixeldive.maxCc="$MAX_CC" \
  :sdk:ktlintCheck :sdk:detekt :sdk:koverVerify
echo "android-sdk ok"
