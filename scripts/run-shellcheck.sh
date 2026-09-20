#!/usr/bin/env bash
# ShellCheck at analog shellcheck_failure_threshold (error; SHELL-LINT-001).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="0.11.0"
ARCHIVE="shellcheck-v${VERSION}.linux.x86_64.tar.xz"
URL="https://github.com/koalaman/shellcheck/releases/download/v${VERSION}/${ARCHIVE}"
SHA256="8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-shellcheck-${VERSION}"
mkdir -p "$WORKDIR"
if [[ ! -x "$WORKDIR/shellcheck" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/$ARCHIVE"
  echo "${SHA256}  $WORKDIR/$ARCHIVE" | sha256sum -c -
  tar -xJf "$WORKDIR/$ARCHIVE" -C "$WORKDIR" --strip-components=1
  chmod +x "$WORKDIR/shellcheck"
fi
shopt -s nullglob
scripts=("$ROOT"/scripts/*.sh)
if ((${#scripts[@]} == 0)); then
  echo "no scripts/*.sh to lint" >&2
  exit 1
fi
exec "$WORKDIR/shellcheck" --severity=error "${scripts[@]}"
