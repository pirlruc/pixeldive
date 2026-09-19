#!/usr/bin/env bash
# Thin wrapper so agents and humans can run github-scaffold issue sync from the repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYNC="$ROOT/.github/scaffold/scripts/issues-sync.py"
if [[ ! -f "$SYNC" ]]; then
  echo "github-scaffold submodule missing at .github/scaffold (TOOL-001-T1)." >&2
  echo "Templates are already synced; analog clone needs Contents: Read." >&2
  exit 1
fi
exec python3 "$SYNC" "$@"
