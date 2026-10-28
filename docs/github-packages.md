# pixeldive

Async image-processing sessions over HTTP and gRPC.

## Package

| Item | Value |
|------|--------|
| GHCR | `ghcr.io/pirlruc/pixeldive` |
| Docker Hub | `pirlruc/pixeldive` (same digest) |
| Architectures | `linux/amd64` |
| User | non-root `65532:65532` |
| Ports | `8000` HTTP, `50051` gRPC |

Release `0.1.0` is the first published image. Prefer a digest.

| Tag | Digest |
|-----|--------|
| `0.1.0` / `latest` | `sha256:2d26235d2882f69dcd4b4196a02c337f144ffd330d566ffa2c43ece835c7b022` (tag index) |
| `0.1.0` `linux/amd64` | `sha256:9da25df190e866825937d27a21bf7bbe6397553d9dcd5ec347c989d86545bf93` |

```bash
docker pull ghcr.io/pirlruc/pixeldive:0.1.0
docker pull ghcr.io/pirlruc/pixeldive@sha256:9da25df190e866825937d27a21bf7bbe6397553d9dcd5ec347c989d86545bf93
```

`ci-run-*` tags are ephemeral CI handoff tags. They are not a release.

## What it does

FastAPI on port 8000 and grpc.aio on port 50051. PostgreSQL stores sessions. Image bytes default to `/data/images`. `/metrics` is unauthenticated Prometheus text on the HTTP port. Do not publish that port on a shared network.

The image sets no database password. Production requires `AUTH_REQUIRED=true`, TLS certificate and key files, and `HTTP_INSECURE=false` plus `GRPC_INSECURE=false`. `AUTO_CREATE_TABLES` defaults to false. Apply Alembic migrations first.

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
  ghcr.io/pirlruc/pixeldive:0.1.0
```

## License

MIT. Source: https://github.com/pirlruc/pixeldive
