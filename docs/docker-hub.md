# pixeldive

Async image-processing sessions over HTTP and gRPC.

## Image

| Item | Value |
|------|--------|
| Docker Hub | `pirlruc/pixeldive` |
| GHCR | `ghcr.io/pirlruc/pixeldive` |
| Architectures | `linux/amd64` |
| User | non-root `65532:65532` |
| Base | `python:3.13.17-slim-trixie` |
| Ports | `8000` HTTP, `50051` gRPC |

Release `0.1.0` is the first published image. The GitHub Release lists the index and `linux/amd64` digests. Prefer that digest. `latest` is never the only tag.

```bash
docker pull pirlruc/pixeldive:0.1.0
```

## What it does

The process serves FastAPI on port 8000 and grpc.aio on port 50051. Session rows live in PostgreSQL. Image bytes default to a local directory. An S3-compatible store is optional.

`/health` and `/ready` are unauthenticated probes. `/metrics` is Prometheus text on the same HTTP port and is not behind API-key auth. Do not publish port 8000 on a shared network if scrapers should be private. There is no separate metrics bind.

## Required configuration

The image has no default database password. Set `DATABASE_URL` before production use. `AUTO_CREATE_TABLES` defaults to false; apply Alembic migrations before serving traffic.

Production (`ENVIRONMENT=production`) requires `AUTH_REQUIRED=true`, TLS certificate and key files, `HTTP_INSECURE=false`, and `GRPC_INSECURE=false`. An auth-disabled bind other than loopback also requires `PIXELDIVE_ALLOW_ANONYMOUS=true`. That flag does not turn TLS off.

| Variable | Role |
|----------|------|
| `DATABASE_URL` | SQLAlchemy URL, including the password |
| `STORAGE_ROOT` | Local blob directory, default `/data/images` |
| `API_KEYS` | Tenant tokens. Duplicate tokens are rejected at startup |
| `TLS_CERT_FILE` / `TLS_KEY_FILE` | PEM pair shared by HTTP and gRPC |
| `HTTP_TLS_CLIENT_CERT_FILE` / `HTTP_TLS_CLIENT_KEY_FILE` | Client certs when the healthcheck must present mTLS |

## Volumes and health

| Path | Purpose |
|------|---------|
| `/data/images` | Local blobs. Mount a writable volume when the root filesystem is read-only |

The image `HEALTHCHECK` runs `python -c "from app.ready_probe import main; main()"`.

## Hardened run

```bash
docker run --rm \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user 65532:65532 \
  -p 127.0.0.1:8000:8000 \
  -p 127.0.0.1:50051:50051 \
  -e DATABASE_URL \
  -e AUTH_REQUIRED=true \
  -e API_KEYS \
  -v pixeldive-images:/data/images \
  pirlruc/pixeldive:0.1.0
```

## Compose

Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` before `docker compose up`. The checked-in Compose file binds published ports to `127.0.0.1`. Source: https://github.com/pirlruc/pixeldive/blob/main/docker-compose.yml

## License

MIT. Source: https://github.com/pirlruc/pixeldive
