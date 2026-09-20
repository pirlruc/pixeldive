# Project-local interpreter and site-packages for CI scripts.
# Supports a stdlib venv, pip --target .venv, and pip --prefix .venv
# (Debian layout: .venv/local/bin + .venv/local/lib/pythonX.Y/dist-packages).
# shellcheck shell=bash
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/local/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/local/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi
export PATH="${ROOT}/.venv/bin:${ROOT}/.venv/local/bin:${PATH}"
for site in \
  "${ROOT}/.venv" \
  "${ROOT}/.venv"/lib/python*/site-packages \
  "${ROOT}/.venv"/local/lib/python*/dist-packages \
  "${ROOT}/.venv"/local/lib/python*/site-packages; do
  if [[ -d "${site}" ]]; then
    export PYTHONPATH="${site}${PYTHONPATH:+:${PYTHONPATH}}"
  fi
done
if [[ -x "${ROOT}/.venv/bin/ruff" ]]; then
  RUFF=("${ROOT}/.venv/bin/ruff")
elif [[ -x "${ROOT}/.venv/local/bin/ruff" ]]; then
  RUFF=("${ROOT}/.venv/local/bin/ruff")
else
  RUFF=("${PYTHON}" -m ruff)
fi
