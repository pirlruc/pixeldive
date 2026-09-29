#!/usr/bin/env bash
# Workflow static analysis (CI-025). Pin matches commondevops common-infra-lint
# (zizmor 1.29.0, --min-severity=low). Installed into a temp prefix so the
# product venv stays the runtime lockfile.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="1.29.0"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-zizmor-${VERSION}"
mkdir -p "$WORKDIR/py"
if [[ ! -x "$WORKDIR/py/bin/zizmor" ]]; then
  python3 -m pip install --disable-pip-version-check --target "$WORKDIR/py" "zizmor==${VERSION}"
fi
export PATH="${WORKDIR}/py/bin:${PATH}"
exec zizmor --min-severity=low "${ROOT}/.github/workflows"
