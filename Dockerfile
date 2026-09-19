# python:3.12.14-slim-bookworm (linux/amd64 digest; DOCKER-BUILD-002/003)
FROM python:3.12.14-slim-bookworm@sha256:356b0d18f9385f4bdcc673af60e1e64c9d1504952e4ec36ee32044c722a6bc4e AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.12.14-slim-bookworm@sha256:356b0d18f9385f4bdcc673af60e1e64c9d1504952e4ec36ee32044c722a6bc4e

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
COPY main.py /app/main.py

RUN mkdir -p /data/images && chown -R 65532:65532 /app /data

USER 65532:65532
EXPOSE 8000 50051
VOLUME ["/data/images"]

# HEALTHCHECK uses stdlib so the runtime image needs no curl (DOCKER-RUN-006).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# Run as non-root numeric UID; config is env-only (DOCKER-RUN-001/004/005).
# Harden with: --read-only --cap-drop ALL --security-opt no-new-privileges
# and a writable mount at /data/images.
ENTRYPOINT ["python", "/app/main.py"]
