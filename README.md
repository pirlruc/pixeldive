# pixeldive

Image-processing **session management** service: Android capture clients open a session with
device/camera identity, then upload frames over REST (multipart) or gRPC (client-streaming).

| Transport | Binding |
|-----------|---------|
| REST | FastAPI `/api/v1/sessions` |
| gRPC | `proto/session_service.proto` (`pixeldive.session.v1.SessionService`) |
| Data | SQLModel + async PostgreSQL (`asyncpg`); Alembic when `AUTO_CREATE_TABLES=false` |
| Blobs | SHA-256 local filesystem, or async S3-compatible adapter (aiobotocore) |
| SDK | `sdk/pixeldive_sdk` (`RestClient`, `GrpcClient`), `ios/` (`PixeldiveSDK`), and `android/` (Kotlin `PixeldiveClient`) |
| Demo | `python -m demo` (web), `ios/Demo` (SwiftUI), and `android/demo` (Compose) |
| Runtime | CPython **3.13** ([QUAL-002](docs/issues.yml), PY-RUN-003) |

Both transports call the same `SessionService` ([ARCH-001](docs/issues.yml)).

## Methodology

[GitHub Issue-native ADR](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr) —
Epic = decision record, optional Y-statement, no ADR markdown files. Templates:
[pirlruc/github-scaffold](https://github.com/pirlruc/github-scaffold) @ 1.5.0. Quality: pin
[pirlruc/guardrails](https://github.com/pirlruc/guardrails) @ 1.6.0 at `docs/guardrails/`. Applies to
**new issues only**. Authored backlog: [`docs/issues.yml`](docs/issues.yml).
Proposed analog additions: [`docs/new-guardrails/`](docs/new-guardrails/).

Android payload shape follows the same keys [FinSilo](https://github.com/pirlruc/finsilo) and
Heimdall clients already read (`Build`, `ActivityManager`, `DisplayMetrics`, Camera2). This repo is
the Python service, not an Android Gradle multi-module clone of Heimdall — do not copy
Heimdall's `app → kit → core` layout. The first-party client lives in `android/` as a
JVM `:sdk` plus a Compose `:demo`.

## Quick start

```bash
# CPython 3.13 (PY-RUN-003). Docker image and CI use 3.13; do not develop on 3.12.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
bash scripts/generate_proto.sh
# tests use SQLite; production default is PostgreSQL
DATABASE_URL=sqlite+aiosqlite:///./pixeldive.db STORAGE_ROOT=./data/images \
  .venv/bin/python main.py
```

If the host has no `ensurepip`/`venv`, install into a project-local prefix instead of the system OS:

```bash
python3 -m pip install --target .venv -r requirements.txt -r requirements-dev.txt
PYTHONPATH=.venv python3 main.py
```

Compose (Postgres + app, local disk). Secrets are not defaulted in the
compose file (DOCKER-COMPOSE-004):

```bash
cp .env.example .env
docker compose up --build
```

S3-compatible path (MinIO profile, OPS-003):

```bash
STORAGE_BACKEND=s3 bash scripts/compose-s3.sh
# or: cp .env.example .env && STORAGE_BACKEND=s3 docker compose --profile s3 up --build
```

Upload one image against that stack:

```bash
curl -F 'file=@frame.png;type=image/png' http://127.0.0.1:8000/api/v1/sessions/<id>/images
```

- REST: `http://127.0.0.1:8000/health`, `/ready`, `/metrics`, `/api/v1/sessions`
- gRPC: `127.0.0.1:50051`

Production-shaped auth: set `ENVIRONMENT=production` (refuses to start without
`AUTH_REQUIRED=true`, `HTTP_INSECURE=false`, and `GRPC_INSECURE=false`), plus
`API_KEYS=token:owner-id` and a PEM pair (`TLS_CERT_FILE` / `TLS_KEY_FILE`, or
the per-transport `HTTP_TLS_*` / `GRPC_TLS_*` files — see `.env.example`). Local
tests keep auth and TLS off. Optional per-tenant quotas:
`RATE_LIMIT_PER_MINUTE`, `TENANT_MAX_UPLOAD_BYTES`, `SESSION_MAX_UPLOAD_BYTES`
(0 = unlimited). Set `GC_MIN_AGE_SECONDS` and `ORPHAN_SWEEP_INTERVAL_SECONDS` to
positive values in production so concurrent same-hash uploads are not collected early.
Process defaults bind HTTP/gRPC to `127.0.0.1`; the Docker image and Compose set
`HTTP_HOST`/`GRPC_HOST` to `0.0.0.0` so the published loopback ports reach the
container.

Python SDK TLS: `RestClient("https://…", token=…, verify="/path/ca.pem")` and
`GrpcClient("host:port", token=…, insecure=False, root_certificates=pem_bytes)`.
iOS/Android clients use platform TLS when the base URL is `https://`; custom CA
loading is [SDK-004](docs/issues.yml).

Compose host ports bind to `127.0.0.1`. Named volumes `pgdata`, `images`, and
`minio` hold state — back them up with `docker compose run --rm` / volume snapshots
before destroying the stack (DOCKER-COMPOSE-008).

## Demo (SDK on an app)

With the session service running:

```bash
PYTHONPATH=sdk:. PIXELDIVE_BASE_URL=http://127.0.0.1:8000 python3 -m demo
```

Open `http://127.0.0.1:8080`. The UI creates Android-shaped sessions, uploads images, and
downloads them through `pixeldive_sdk.RestClient`.

iOS: open [`ios/README.md`](ios/README.md). `PixeldiveClient` is the Swift twin of
`RestClient`. The SwiftUI demo (`ios/Demo/PixeldiveDemo.xcodeproj`) talks to the service
only through that package. Session JSON keeps Android wire keys; iOS identity is mapped
from `UIDevice` / `AVCaptureDevice` and tagged `metadata.platform=ios`.

Android: open [`android/README.md`](android/README.md). The Kotlin `PixeldiveClient` is
the JVM twin of `RestClient`. The Compose demo (`android/demo`) talks to the service
only through that library and maps `Build` / Camera2 into the same keys, tagged
`metadata.platform=android`.

## Quality gates

```bash
bash scripts/ci-local.sh
# macOS / Linux-with-Swift: Foundation package tests (SWIFT-TEST-001)
PIXELDIVE_REQUIRE_SWIFT=1 bash scripts/check-ios-sdk.sh
# Linux-with-JDK: Kotlin JVM package tests (KT-TEST-001)
PIXELDIVE_REQUIRE_JAVA=1 bash scripts/check-android-sdk.sh
```

PostgreSQL integration (CI job `postgres` / DATA-003), not the local default:

```bash
PIXELDIVE_TEST_DATABASE_URL=postgresql+asyncpg://pixeldive:pixeldive@127.0.0.1:5432/pixeldive \
  bash scripts/ci-postgres.sh
```

Floors live in `config/python.profile.thresholds.yml` (PY-TEST-002 95/95, PY-DOC-001, PY-CPLX-* max CC 8)
and `config/swift.profile.thresholds.yml` (SWIFT-TEST-002 95 line coverage overlay)
and `config/kotlin.profile.thresholds.yml` (KT-TEST-002 95/95).
When `GUARDRAILS_READ_TOKEN` is set, CI clones the analog pin and refuses a **looser** overlay (CI-022).
Stricter values (avg MI 70 vs org 60; Swift statement coverage 95 vs org 90) are allowed. `docs/guardrail-deviations.yml` is empty.
`uv.lock` is the PY-RUN-001 lockfile; `requirements.txt` is the pip/Docker freeze
(`uv export`). Local `scripts/ci-local.sh` also runs pydoclint, hadolint, KICS,
ShellCheck, and markdown link lint.

## Agent handoff

See [`docs/ai-agent-handoff.md`](docs/ai-agent-handoff.md).
