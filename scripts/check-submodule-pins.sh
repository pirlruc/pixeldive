#!/bin/sh
# SC-DEP-004: gitlink SHA must equal the peeled annotated tag named here.
# common-pins-verify runs this file with sh, so it stays POSIX.
# Does not clone the private submodules; it reads the gitlink in HEAD.
set -eu

ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

# Peeled commits for annotated tags guardrails 1.13.1 and github-scaffold 1.10.2.
GR_TAG="1.13.1"
GR_EXPECT="1945211ac851c3c0f83694bd4ea53571fdced4ab"
SC_TAG="1.10.2"
SC_EXPECT="c8eddcfb2c8a808981e640fa9739cb4fcefa991e"

gr="$(git rev-parse 'HEAD:docs/guardrails')"
sc="$(git rev-parse 'HEAD:.github/scaffold')"

status=0
if [ "${gr}" != "${GR_EXPECT}" ]; then
  echo "SC-DEP-004: docs/guardrails gitlink ${gr} != ${GR_TAG} ${GR_EXPECT}" >&2
  status=1
fi
if [ "${sc}" != "${SC_EXPECT}" ]; then
  echo "SC-DEP-004: .github/scaffold gitlink ${sc} != ${SC_TAG} ${SC_EXPECT}" >&2
  status=1
fi
if [ "${status}" -ne 0 ]; then
  exit 1
fi

echo "SC-DEP-004: docs/guardrails @ ${GR_TAG} (${GR_EXPECT})"
echo "SC-DEP-004: .github/scaffold @ ${SC_TAG} (${SC_EXPECT})"
