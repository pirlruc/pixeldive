#!/usr/bin/env bash
# PY-RUN-001: requirements.txt is the pip/Docker freeze of uv.lock.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to verify requirements.txt against uv.lock (PY-RUN-001)" >&2
  exit 1
fi
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
uv export --frozen --no-dev --no-hashes --no-emit-project --no-annotate --no-header -o "$tmp"
diff -u "$ROOT/requirements.txt" "$tmp"
echo "requirements.txt matches uv export"
