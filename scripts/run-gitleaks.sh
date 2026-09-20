#!/usr/bin/env bash
# Local/CI runner for a checksum-pinned gitleaks binary (secret scan).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="8.30.1"
ARCHIVE="gitleaks_${VERSION}_linux_x64.tar.gz"
URL="https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/${ARCHIVE}"
SHA256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-gitleaks-${VERSION}"
mkdir -p "$WORKDIR"
if [[ ! -x "$WORKDIR/gitleaks" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/$ARCHIVE"
  echo "${SHA256}  $WORKDIR/$ARCHIVE" | sha256sum -c -
  tar -xzf "$WORKDIR/$ARCHIVE" -C "$WORKDIR" gitleaks
  chmod +x "$WORKDIR/gitleaks"
fi
cd "$ROOT"
exec "$WORKDIR/gitleaks" detect --source "$ROOT" --verbose --redact --exit-code 1 "$@"
