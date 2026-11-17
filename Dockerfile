# dhi.io/python:3.13-debian13-dev (linux/amd64). The runtime tag has no shell,
# so the venv and the data directory are prepared here.
# CPython minor follows PY-RUN-003 / guardrails python/profile.md (3.13;
# 3.14 is still in bugfix until ~2027-10, so it does not qualify until the
# 2027-04 re-evaluation). Keep lockstep with setup-python and requires-python.
FROM dhi.io/python:3.13-debian13-dev@sha256:dbe603d026e33548f420346eb3963d3dd385a06148c1913bb5af32218829d4e2 AS builder

WORKDIR /build
# --without-pip keeps pip/setuptools/msgpack out of the runtime venv
# (DOCKER-BUILD-001). Install with the builder image's pip.
RUN python -m venv --without-pip /opt/venv \
 && install -d -o 65532 -g 65532 /out/data/images
COPY requirements.txt .
RUN pip --python /opt/venv/bin/python install --no-cache-dir -r requirements.txt

# dhi.io/python:3.13-debian13 (linux/amd64). No /bin/sh, so this stage has
# no RUN. The base user is 65532 and cannot delete the image's own pip.
FROM dhi.io/python:3.13-debian13@sha256:ab678ca8fa69d36f1386fb71f4252d1a9561b7542ca84f5d14babffebcf4f479

LABEL org.opencontainers.image.title="pixeldive" \
      org.opencontainers.image.description="Image-processing session management (REST + gRPC)" \
      org.opencontainers.image.source="https://github.com/pirlruc/pixeldive" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    STORAGE_ROOT="/data/images" \
    HTTP_HOST="0.0.0.0" \
    HTTP_PORT="8000" \
    GRPC_HOST="0.0.0.0" \
    GRPC_PORT="50051"

# DOCKER-BUILD-007: chown on COPY, not a follow-up RUN that rewrites the tree.
# kics-scan ignore-line
COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv

# The data directory is created in the builder. This image has no shell,
# so it cannot RUN install or delete the base image's /usr/bin/pip.
COPY --from=builder --chown=65532:65532 /out/data/images /data/images

WORKDIR /app
# kics-scan ignore-line
COPY --chown=65532:65532 app /app/app
# kics-scan ignore-line
COPY --chown=65532:65532 proto /app/proto
# kics-scan ignore-line
COPY --chown=65532:65532 migrations /app/migrations
# kics-scan ignore-line
COPY --chown=65532:65532 alembic.ini /app/alembic.ini
# kics-scan ignore-line
COPY --chown=65532:65532 main.py /app/main.py

USER 65532:65532
EXPOSE 8000 50051
VOLUME ["/data/images"]

# HEALTHCHECK uses stdlib so the runtime image needs no curl (DOCKER-RUN-006).
# ready_probe selects HTTP or HTTPS from HTTP_INSECURE / TLS_* env.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-c", "from app.ready_probe import main; main()"]

# Run as non-root numeric UID; config is env-only (DOCKER-RUN-001/004/005).
# Harden with: --read-only --cap-drop ALL --security-opt no-new-privileges
# and a writable mount at /data/images.
ENTRYPOINT ["python", "/app/main.py"]
