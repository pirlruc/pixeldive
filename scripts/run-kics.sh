#!/usr/bin/env bash
# Dockerfile + Compose IaC scan (DOCKER-LINT-002). KICS fail-on high,medium
# matches docs/guardrails/docker/profile.thresholds.yml iac_fail_on.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="2.1.20"
ARCHIVE="kics_${VERSION}_linux_amd64.tar.gz"
URL="https://github.com/Checkmarx/kics/releases/download/v${VERSION}/${ARCHIVE}"
SHA256="8a5aa375ccfdc0ddd1114eddf1f9638ad7f6122e98d12a592207509dbe6d81f8"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-kics-${VERSION}"
mkdir -p "$WORKDIR"
if [[ ! -x "$WORKDIR/kics" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/$ARCHIVE"
  echo "${SHA256}  $WORKDIR/$ARCHIVE" | sha256sum -c -
  tar -xzf "$WORKDIR/$ARCHIVE" -C "$WORKDIR" kics
  chmod +x "$WORKDIR/kics"
fi
QUERIES="$WORKDIR/queries"
if [[ ! -d "$WORKDIR/kics-src/assets/queries/dockerfile" ]]; then
  rm -rf "$WORKDIR/kics-src"
  git clone --depth 1 --filter=blob:none --sparse --branch "v${VERSION}" \
    https://github.com/Checkmarx/kics.git "$WORKDIR/kics-src"
  git -C "$WORKDIR/kics-src" sparse-checkout set assets/queries
fi
if [[ -d "$WORKDIR/kics-src/assets/queries" ]]; then
  QUERIES="$WORKDIR/kics-src/assets/queries"
fi
mkdir -p "$WORKDIR/out"
"$WORKDIR/kics" scan \
  --ci \
  --no-progress \
  --fail-on high,medium \
  --queries-path "$QUERIES" \
  --path "$ROOT/Dockerfile" \
  --path "$ROOT/docker-compose.yml" \
  --output-path "$WORKDIR/out"
