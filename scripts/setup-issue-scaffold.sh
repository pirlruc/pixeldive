#!/usr/bin/env bash
# Thin wrapper: create methodology labels and milestones from docs/issues-sync-targets.yml.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SETUP="$ROOT/.github/scaffold/scripts/setup-issue-scaffold.sh"
if [[ ! -f "$SETUP" ]]; then
  echo "github-scaffold submodule missing at .github/scaffold (TOOL-001-T1)." >&2
  exit 1
fi
exec bash "$SETUP" "$@"
