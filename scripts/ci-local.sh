#!/usr/bin/env bash
# Local parity for PY-* gates (python-quality-gates.mdc).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=python-env.sh
source "$ROOT/scripts/python-env.sh"

"$PYTHON" scripts/read_python_threshold.py statement_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py branch_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py doc_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py max_cyclomatic_complexity >/dev/null

STMT="$("$PYTHON" scripts/read_python_threshold.py statement_coverage)"
BRANCH="$("$PYTHON" scripts/read_python_threshold.py branch_coverage)"
DOC="$("$PYTHON" scripts/read_python_threshold.py doc_coverage)"

"${RUFF[@]}" check app main.py tests scripts sdk demo
"${RUFF[@]}" format --check app main.py tests scripts sdk demo
"$PYTHON" -m mypy app main.py sdk demo
"$PYTHON" scripts/check-complexity.py
"$PYTHON" -m interrogate -c pyproject.toml app main.py sdk demo
"$PYTHON" scripts/run-pydoclint.py --config pyproject.toml app main.py sdk demo
"$PYTHON" -m bandit -q -r app main.py sdk demo -x app/pb
"$PYTHON" -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off
bash "$ROOT/scripts/check-submodule-pins.sh"
# On GitHub Actions these tools belong to ops-reuse.yml (non-dependabot) or
# the docker-lint job (dependabot). Local runs still execute them here.
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  echo "skipping hadolint, kics, shellcheck, actionlint, zizmor (workflow jobs own them)"
else
  bash "$ROOT/scripts/run-hadolint.sh"
  bash "$ROOT/scripts/run-kics.sh"
  bash "$ROOT/scripts/run-shellcheck.sh"
  bash "$ROOT/scripts/run-actionlint.sh"
  bash "$ROOT/scripts/run-zizmor.sh"
fi
"$PYTHON" scripts/lint-doc-links.py --root "$ROOT"
"$PYTHON" -m pytest \
  --cov=app --cov=main --cov=sdk --cov=demo --cov-branch \
  --cov-fail-under="${STMT}" \
  -q
# ios-sdk and android-sdk are the fail-closed mobile jobs. A partial Swift
# or Java on the Ubuntu quality runner must not fail the Python gate.
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  echo "skipping ios and android SDK gates (dedicated jobs own them)"
else
  bash "$ROOT/scripts/check-ios-sdk.sh"
  bash "$ROOT/scripts/check-android-sdk.sh"
fi
echo "ci-local ok (statement_coverage=${STMT} branch_coverage=${BRANCH} doc_coverage=${DOC})"
