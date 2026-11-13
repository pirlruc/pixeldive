#!/usr/bin/env bash
# Workflow static analysis (CI-025). Pin matches commondevops common-infra-lint
# (zizmor 1.29.0, --min-severity=low). Installed into a temp prefix so the
# product venv stays the runtime lockfile.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
exec uv run --frozen --group dev zizmor --min-severity=low .github/workflows
