#!/usr/bin/env bash
# Image build, structure test, and supply-chain scanners (CI-008).
# Host PATH first. Missing tools run from the published toolchain images.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SUPPLY_IMAGE="${PIXELDIVE_SUPPLY_IMAGE:-ghcr.io/pirlruc/ci-supply-chain@sha256:2afa89cd956049503cb4ffb67b4079963e09906fcfc0c3e8ffd68286f93bb341}"
CST_IMAGE="${PIXELDIVE_CST_IMAGE:-ghcr.io/pirlruc/ci-container@sha256:8895fe81e776dd2a3ea4ca2bfae0c94cd7d8a45f20df027c715c1278946b1363}"
IMAGE="${PIXELDIVE_IMAGE:-pixeldive:ci}"
SWIFT_IMAGE="${PIXELDIVE_SWIFT_IMAGE:-swift:6.1}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for host-unavailable CI checks" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker engine is not running" >&2
  exit 1
fi

# Same engine as `docker build`. Docker Desktop's current context is a
# user socket, not /var/run/docker.sock.
DOCKER_SOCK="/var/run/docker.sock"
endpoint="$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null || true)"
case "${endpoint}" in
unix://*)
  DOCKER_SOCK="${endpoint#unix://}"
  ;;
esac
if [[ ! -S "${DOCKER_SOCK}" ]]; then
  echo "docker socket is not usable: ${DOCKER_SOCK}" >&2
  exit 1
fi
# The published scanner images run as uid 1000. The engine socket is mode
# 660 and root-owned, so those containers must be root to dial it.

echo "==> docker build ${IMAGE}"
docker buildx build --load -t "${IMAGE}" "${ROOT}"

if command -v container-structure-test >/dev/null 2>&1; then
  container-structure-test test --image "${IMAGE}" --config "${ROOT}/container-structure-test.yml"
else
  echo "==> container-structure-test via ${CST_IMAGE}"
  docker pull "${CST_IMAGE}"
  docker run --rm --user 0 \
    -v "${DOCKER_SOCK}:/var/run/docker.sock" \
    -v "${ROOT}/container-structure-test.yml:/config.yml:ro" \
    --entrypoint container-structure-test \
    "${CST_IMAGE}" \
    test --image "${IMAGE}" --config /config.yml
fi

echo "==> trivy, grype, syft via ${SUPPLY_IMAGE}"
docker pull "${SUPPLY_IMAGE}"
docker run --rm --user 0 \
  -v "${DOCKER_SOCK}:/var/run/docker.sock" \
  --entrypoint trivy \
  "${SUPPLY_IMAGE}" \
  image --scanners vuln,secret --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "${IMAGE}"
# --only-fixed matches trivy --ignore-unfixed. Debian "won't fix" highs
# stay visible in the report and do not fail the gate.
docker run --rm --user 0 \
  -v "${DOCKER_SOCK}:/var/run/docker.sock" \
  --entrypoint grype \
  "${SUPPLY_IMAGE}" \
  "${IMAGE}" --only-fixed --fail-on high
docker run --rm --user 0 \
  -v "${DOCKER_SOCK}:/var/run/docker.sock" \
  --entrypoint syft \
  "${SUPPLY_IMAGE}" \
  "${IMAGE}" -o cyclonedx-json=/tmp/pixeldive.cdx.json >/dev/null

if ! command -v swift >/dev/null 2>&1; then
  echo "==> swift test via ${SWIFT_IMAGE}"
  docker pull "${SWIFT_IMAGE}"
  docker run --rm \
    -v "${ROOT}:/workspace" \
    -w /workspace/ios \
    -e TMPDIR=/tmp \
    "${SWIFT_IMAGE}" \
    swift test --package-path /workspace/ios
fi

echo "check-ci-docker ok"
