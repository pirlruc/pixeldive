#!/usr/bin/env bash
# PostgreSQL integration path for DATA-003. SQLite remains the default for
# scripts/check-ci-local.sh (PY-TEST-002).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=python-env.sh
source "$ROOT/scripts/python-env.sh"

: "${PIXELDIVE_TEST_DATABASE_URL:?set PIXELDIVE_TEST_DATABASE_URL to a postgresql+asyncpg URL}"
"$PYTHON" - <<'PY'
import os

from app.migrate import check_sync, upgrade_head_sync

url = os.environ["PIXELDIVE_TEST_DATABASE_URL"]
upgrade_head_sync(url)
check_sync(url)
PY
"$PYTHON" -m pytest tests/test_service.py tests/test_api.py tests/test_phase2.py tests/test_phase3.py tests/test_quota_store.py tests/test_sdk.py \
  --cov-fail-under=0 -q
echo "ci-postgres ok"
