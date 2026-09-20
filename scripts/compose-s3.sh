#!/usr/bin/env bash
# Boot Compose with MinIO and STORAGE_BACKEND=s3 (OPS-003).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export STORAGE_BACKEND=s3
export S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://minio:9000}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-minioadmin}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-minioadmin}"
exec docker compose --profile s3 up --build "$@"
