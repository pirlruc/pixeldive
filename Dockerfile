# python:3.13.15-slim-bookworm (linux/amd64 digest; DOCKER-BUILD-002/003).
# CPython minor follows PY-RUN-003 / guardrails python/profile.md (3.13;
# 3.14 is still in bugfix until ~2027-10, so it does not qualify until the
# 2027-04 re-evaluation). Keep lockstep with setup-python and requires-python.
FROM python:3.13.15-slim-bookworm@sha256:3e2de9c40ca4e3d73240059f9d48baff27908f10293e985a2f382a0378e6df4a AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

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

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY app /app/app
COPY proto /app/proto
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY main.py /app/main.py

RUN mkdir -p /data/images && chown -R 65532:65532 /app /data

USER 65532:65532
EXPOSE 8000 50051
VOLUME ["/data/images"]

# HEALTHCHECK uses stdlib so the runtime image needs no curl (DOCKER-RUN-006).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')"

# Run as non-root numeric UID; config is env-only (DOCKER-RUN-001/004/005).
# Harden with: --read-only --cap-drop ALL --security-opt no-new-privileges
# and a writable mount at /data/images.
ENTRYPOINT ["python", "/app/main.py"]
