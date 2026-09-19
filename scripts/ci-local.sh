#!/usr/bin/env bash
# Local parity for PY-* gates (python-quality-gates.mdc).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -d "$ROOT/.venv" ]]; then
  export PYTHONPATH="$ROOT/.venv${PYTHONPATH:+:$PYTHONPATH}"
  export PATH="$ROOT/.venv/bin:${PATH}"
fi

"$PYTHON" scripts/read_python_threshold.py statement_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py branch_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py doc_coverage >/dev/null
"$PYTHON" scripts/read_python_threshold.py max_cyclomatic_complexity >/dev/null

STMT="$("$PYTHON" scripts/read_python_threshold.py statement_coverage)"
BRANCH="$("$PYTHON" scripts/read_python_threshold.py branch_coverage)"
DOC="$("$PYTHON" scripts/read_python_threshold.py doc_coverage)"

if [[ -x "$ROOT/.venv/bin/ruff" ]]; then
  RUFF=("$ROOT/.venv/bin/ruff")
else
  RUFF=("$PYTHON" -m ruff)
fi

"${RUFF[@]}" check app main.py tests scripts sdk demo
"${RUFF[@]}" format --check app main.py tests scripts sdk demo
"$PYTHON" -m mypy app main.py sdk demo
"$PYTHON" scripts/check-complexity.py
"$PYTHON" -m interrogate -c pyproject.toml app main.py sdk demo
"$PYTHON" -m pytest \
  --cov=app --cov=main --cov=sdk --cov=demo --cov-branch \
  --cov-fail-under="${STMT}" \
  -q
echo "ci-local ok (statement_coverage=${STMT} branch_coverage=${BRANCH} doc_coverage=${DOC})"
