# pixeldive

Image-processing **session management** service: Android capture clients open a session with
device/camera identity, then upload frames over REST (multipart) or gRPC (client-streaming).

| Transport | Binding |
|-----------|---------|
| REST | FastAPI `/api/v1/sessions` |
| gRPC | `proto/session_service.proto` (`pixeldive.session.v1.SessionService`) |
| Data | SQLModel + async PostgreSQL (`asyncpg`) |
| Blobs | SHA-256 local filesystem, or S3-compatible adapter |

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

Compose (Postgres + app):

```bash
docker compose up --build
```

- REST: `http://127.0.0.1:8000/health` and `/api/v1/sessions`
- gRPC: `127.0.0.1:50051`

## Quality gates

```bash
bash scripts/ci-local.sh
```

Floors live in `config/python.profile.thresholds.yml` (PY-TEST-002 95/95, PY-DOC-001, PY-CPLX-*).
When `GUARDRAILS_READ_TOKEN` is set, CI clones the analog pin and refuses drift (CI-022).

## Agent handoff

See [`docs/ai-agent-handoff.md`](docs/ai-agent-handoff.md).
