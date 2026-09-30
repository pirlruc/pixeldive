#!/usr/bin/env bash
# SC-DEP-004: gitlink SHA must equal the peeled annotated tag named here.
# Does not clone the private submodules; it reads the gitlink in HEAD.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

# Peeled commits for annotated tags guardrails 1.8.0 and github-scaffold 1.7.0.
GR_TAG="1.8.0"
GR_EXPECT="aa5184ceaa5d005a71d984fd771564cb10b63681"
SC_TAG="1.7.0"
SC_EXPECT="e76bb3fda306c490b4b3ea5e1a4e3977e04a1a1d"

gr="$(git rev-parse 'HEAD:docs/guardrails')"
sc="$(git rev-parse 'HEAD:.github/scaffold')"

status=0
if [[ "${gr}" != "${GR_EXPECT}" ]]; then
  echo "SC-DEP-004: docs/guardrails gitlink ${gr} != ${GR_TAG} ${GR_EXPECT}" >&2
  status=1
fi
if [[ "${sc}" != "${SC_EXPECT}" ]]; then
  echo "SC-DEP-004: .github/scaffold gitlink ${sc} != ${SC_TAG} ${SC_EXPECT}" >&2
  status=1
fi
if [[ "${status}" -ne 0 ]]; then
  exit 1
fi

echo "SC-DEP-004: docs/guardrails @ ${GR_TAG} (${GR_EXPECT})"
echo "SC-DEP-004: .github/scaffold @ ${SC_TAG} (${SC_EXPECT})"
