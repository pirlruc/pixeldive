# pixeldive

Image-processing **session management** service: Android capture clients open a session with
device/camera identity, then upload frames over REST (multipart) or gRPC (client-streaming).

| Transport | Binding |
|-----------|---------|
| REST | FastAPI `/api/v1/sessions` |
| gRPC | `proto/session_service.proto` (`pixeldive.session.v1.SessionService`) |
| Data | SQLModel + async PostgreSQL (`asyncpg`); Alembic when `AUTO_CREATE_TABLES=false` |
| Blobs | SHA-256 local filesystem, or async S3-compatible adapter (aiobotocore) |
| SDK | `sdk/pixeldive_sdk` (`RestClient`, `GrpcClient`) |
| Demo | `python -m demo` (FastAPI UI that talks to the service only through the SDK) |

Both transports call the same `SessionService` ([ARCH-001](docs/issues.yml)).

## Methodology

[GitHub Issue-native ADR](https://github.com/pirlruc/methodologies/tree/1.2.0/github-issue-adr) —
Epic = decision record, optional Y-statement, no ADR markdown files. Templates:
[pirlruc/github-scaffold](https://github.com/pirlruc/github-scaffold) @ 1.2.0. Quality: pin
[pirlruc/guardrails](https://github.com/pirlruc/guardrails) at `docs/guardrails/`. Applies to
**new issues only**. Authored backlog: [`docs/issues.yml`](docs/issues.yml).

Android payload shape follows the same keys [FinSilo](https://github.com/pirlruc/finsilo) and
Heimdall clients already read (`Build`, `ActivityManager`, `DisplayMetrics`, Camera2). This repo is
the Python service, not an Android app — do not copy Heimdall's `app → kit → core` Gradle layout.

## Quick start

```bash
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

Compose (Postgres + app, local disk):

```bash
docker compose up --build
```

S3-compatible path (MinIO profile, OPS-003):

```bash
STORAGE_BACKEND=s3 bash scripts/compose-s3.sh
# or: STORAGE_BACKEND=s3 docker compose --profile s3 up --build
```

Upload one image against that stack:

```bash
curl -F 'file=@frame.png;type=image/png' http://127.0.0.1:8000/api/v1/sessions/<id>/images
```

- REST: `http://127.0.0.1:8000/health`, `/ready`, `/metrics`, `/api/v1/sessions`
- gRPC: `127.0.0.1:50051`

Production-shaped auth: set `AUTH_REQUIRED=true` and `API_KEYS=token:owner-id` (see `.env.example`).
Optional per-tenant quotas: `RATE_LIMIT_PER_MINUTE`, `TENANT_MAX_UPLOAD_BYTES`,
`SESSION_MAX_UPLOAD_BYTES` (0 = unlimited). gRPC TLS is off until `GRPC_INSECURE=false`
plus cert/key paths. Set `GC_MIN_AGE_SECONDS` and `ORPHAN_SWEEP_INTERVAL_SECONDS` to
positive values in production so concurrent same-hash uploads are not collected early.

## Demo (SDK on an app)

With the session service running:

```bash
PYTHONPATH=sdk:. PIXELDIVE_BASE_URL=http://127.0.0.1:8000 python3 -m demo
```

Open `http://127.0.0.1:8080`. The UI creates Android-shaped sessions, uploads images, and
downloads them through `pixeldive_sdk.RestClient`.

## Quality gates

```bash
bash scripts/ci-local.sh
```

PostgreSQL integration (CI job `postgres` / DATA-003), not the local default:

```bash
PIXELDIVE_TEST_DATABASE_URL=postgresql+asyncpg://pixeldive:pixeldive@127.0.0.1:5432/pixeldive \
  bash scripts/ci-postgres.sh
```

Floors live in `config/python.profile.thresholds.yml` (PY-TEST-002 95/95, PY-DOC-001, PY-CPLX-*).
When `GUARDRAILS_READ_TOKEN` is set, CI clones the analog pin and refuses drift (CI-022).
`docs/guardrail-deviations.yml` is empty — gates are not lowered.

## Agent handoff

See [`docs/ai-agent-handoff.md`](docs/ai-agent-handoff.md).
