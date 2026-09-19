#!/usr/bin/env bash
# Sync GitHub templates and Cursor rules from the github-scaffold submodule.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYNC="$ROOT/.github/scaffold/scripts/sync-templates.sh"
if [[ ! -f "$SYNC" ]]; then
  echo "github-scaffold submodule missing at .github/scaffold (TOOL-001-T1)." >&2
  echo "Checked-in templates under .github/ and .cursor/rules/ remain the working copies." >&2
  exit 1
fi
exec bash "$SYNC" "$@"
