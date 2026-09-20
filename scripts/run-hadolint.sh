#!/usr/bin/env bash
# Dockerfile lint (DOCKER-LINT-001). Fail at warning, matching
# docs/guardrails/docker/profile.thresholds.yml hadolint_failure_threshold.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="2.15.1"
URL="https://github.com/hadolint/hadolint/releases/download/v${VERSION}/hadolint-Linux-x86_64"
SHA256="c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-hadolint-${VERSION}"
mkdir -p "$WORKDIR"
if [[ ! -x "$WORKDIR/hadolint" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/hadolint"
  echo "${SHA256}  $WORKDIR/hadolint" | sha256sum -c -
  chmod +x "$WORKDIR/hadolint"
fi
exec "$WORKDIR/hadolint" --failure-threshold warning "$ROOT/Dockerfile"
