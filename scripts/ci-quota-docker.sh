#!/usr/bin/env bash
# Shared quota tests against Compose PostgreSQL and the redis profile.
# SQLite remains the default for scripts/check-ci-local.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=python-env.sh
source "$ROOT/scripts/python-env.sh"

export POSTGRES_USER="${POSTGRES_USER:-pixeldive}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-pixeldive}"
export POSTGRES_DB="${POSTGRES_DB:-pixeldive}"
export PIXELDIVE_TEST_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

docker compose up -d db
docker compose --profile redis up -d redis

ready=0
for _ in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1 \
    && docker compose --profile redis exec -T redis redis-cli ping >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "postgres or redis did not become ready" >&2
  exit 1
fi

"$PYTHON" -m pytest tests/test_quota_store.py -q --cov-fail-under=0
echo "ci-quota-docker ok"
