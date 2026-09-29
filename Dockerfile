# python:3.13.15-slim-bookworm (linux/amd64 digest; DOCKER-BUILD-002/003).
# CPython minor follows PY-RUN-003 / guardrails python/profile.md (3.13;
# 3.14 is still in bugfix until ~2027-10, so it does not qualify until the
# 2027-04 re-evaluation). Keep lockstep with setup-python and requires-python.
FROM python:3.13.15-slim-bookworm@sha256:3e2de9c40ca4e3d73240059f9d48baff27908f10293e985a2f382a0378e6df4a AS builder

WORKDIR /build
# --without-pip keeps pip/setuptools/msgpack out of the runtime venv
# (DOCKER-BUILD-001). Install with the builder image's pip.
RUN python -m venv --without-pip /opt/venv
COPY requirements.txt .
RUN pip --python /opt/venv/bin/python install --no-cache-dir -r requirements.txt

FROM python:3.13.15-slim-bookworm@sha256:3e2de9c40ca4e3d73240059f9d48baff27908f10293e985a2f382a0378e6df4a

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
COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv

# Official python-slim ships pip/setuptools in /usr/local (CVE-2025-47273).
# They are build tooling, not runtime (DOCKER-BUILD-001).
RUN rm -rf \
      /usr/local/lib/python3.13/ensurepip \
      /usr/local/bin/pip \
      /usr/local/bin/pip3 \
      /usr/local/bin/pip3.13 \
      /usr/local/bin/wheel \
 && find /usr/local/lib/python3.13/site-packages -maxdepth 1 \( \
      -name 'pip' -o -name 'pip-*' -o \
      -name 'setuptools' -o -name 'setuptools-*' -o \
      -name '_distutils_hack' -o -name 'pkg_resources' -o \
      -name 'wheel' -o -name 'wheel-*' \
    \) -exec rm -rf {} +

WORKDIR /app
COPY --chown=65532:65532 app /app/app
COPY --chown=65532:65532 proto /app/proto
COPY --chown=65532:65532 migrations /app/migrations
COPY --chown=65532:65532 alembic.ini /app/alembic.ini
COPY --chown=65532:65532 main.py /app/main.py

USER 65532:65532
RUN mkdir -p /data/images
EXPOSE 8000 50051
VOLUME ["/data/images"]

# HEALTHCHECK uses stdlib so the runtime image needs no curl (DOCKER-RUN-006).
# ready_probe selects HTTP or HTTPS from HTTP_INSECURE / TLS_* env.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-c", "from app.ready_probe import main; main()"]

# Run as non-root numeric UID; config is env-only (DOCKER-RUN-001/004/005).
# Harden with: --read-only --cap-drop ALL --security-opt no-new-privileges
# and a writable mount at /data/images.
ENTRYPOINT ["python", "/app/main.py"]
