#!/usr/bin/env bash
# Workflow lint (CI-023). Version matches commondevops common-infra-lint
# (actionlint 1.7.12). Product CI cannot call that private reusable until
# COMMONDEVOPS_READ_TOKEN exists; this script is the in-repo gate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="1.7.12"
ARCHIVE="actionlint_${VERSION}_linux_amd64.tar.gz"
URL="https://github.com/rhysd/actionlint/releases/download/v${VERSION}/${ARCHIVE}"
SHA256="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-actionlint-${VERSION}"
mkdir -p "$WORKDIR"
if [[ ! -x "$WORKDIR/actionlint" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/$ARCHIVE"
  echo "${SHA256}  $WORKDIR/$ARCHIVE" | sha256sum -c -
  tar -xzf "$WORKDIR/$ARCHIVE" -C "$WORKDIR" actionlint
  chmod +x "$WORKDIR/actionlint"
fi
shopt -s nullglob
workflows=("$ROOT"/.github/workflows/*.yml)
if ((${#workflows[@]} == 0)); then
  echo "no workflows to lint" >&2
  exit 1
fi
exec "$WORKDIR/actionlint" "${workflows[@]}"
