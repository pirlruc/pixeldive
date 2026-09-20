# AI Agent Handoff — pixeldive

## Identity

| Field | Value |
| --- | --- |
| **Service** | pixeldive |
| **Type** | Async Python microservice (FastAPI REST + gRPC) for image-processing sessions |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/new-guardrails/` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Phase 1 session platform is **on main** ([PR #1](https://github.com/pirlruc/pixeldive/pull/1), merged 2026-09-19). Phase 2 hardening, Python SDK, capture demo, and async S3 (PERF-002) are **on main** ([PR #7](https://github.com/pirlruc/pixeldive/pull/7), merged 2026-09-19). Phase 3 remaining hardening is **on main** ([PR #9](https://github.com/pirlruc/pixeldive/pull/9)). Analog pins, DRY, and 1.6.0 compliance are on this branch.

GitHub Epic/Task issues are not published ([TOOL-002](issues.yml)); statuses live in [`docs/issues.yml`](issues.yml).

| Module | Path | Notes |
| --- | --- | --- |
| models | `app/models.py`, `app/schemas.py` | SQLModel tables + Android-aligned JSON payloads; `storage_path` is internal |
| service | `app/service.py` | Single business layer for REST and gRPC (mixins for list/ingest/batch) |
| quotas | `app/quotas.py` | In-process per-tenant caps with a lock (SEC-002); shared Postgres is SEC-004 |
| REST | `app/api.py`, `app/api_images.py` | FastAPI `/api/v1` + `/health` `/ready` `/metrics` |
| gRPC | `app/grpc_server.py`, `app/grpc_rpc.py`, `proto/session_service.proto` | aio servicer; unary RPCs share `run_unary` |
| errors | `app/error_map.py` | One exception → HTTP/gRPC table |
| storage | `app/local_storage.py`, `app/s3_storage.py`, `app/s3_multipart.py` | SHA-256 local FS + async S3 multipart PUT |
| lifecycle | `app/lifecycle.py`, `main.py` | Coordinated HTTP/gRPC stop, storage `aclose`, optional orphan sweep |
| SDK | `sdk/pixeldive_sdk/` | `RestClient` (`_json` helper) + `GrpcClient` (`GrpcHostMixin`) |
| demo | `demo/` | FastAPI UI that uses only the SDK |
| runner | `main.py` | Uvicorn + grpc.aio on one asyncio loop |

## How to run checks

Prefer tools already on PATH, then a project-local env (not a system OS install):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
bash scripts/generate_proto.sh
bash scripts/ci-local.sh
```

If `ensurepip` is missing:

```bash
python3 -m pip install --target .venv -r requirements.txt -r requirements-dev.txt
PYTHONPATH=.venv bash scripts/ci-local.sh
```

CI: `.github/workflows/quality.yml` (SQLite PY-* plus `postgres` Alembic job), `security.yml` (gitleaks, CodeQL, bandit, pip-audit, dependency-review). Actions are SHA-pinned. Numeric gates read analog `docs/guardrails/python/profile.thresholds.yml` after `scripts/ci-init-guardrails.sh` (`GUARDRAILS_READ_TOKEN`); otherwise the consumer copy `config/python.profile.thresholds.yml`. The overlay reader allows stricter consumer values and fails on looser ones. Do not clone `.github/scaffold` in CI.

## Analog pins (TOOL-001)

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Git submodule at `docs/guardrails/` (tag **1.6.0**). Private; needs `GUARDRAILS_READ_TOKEN`. |
| `pirlruc/github-scaffold` | Git submodule at `.github/scaffold/` (tag **1.5.0**). Templates are synced into `.github/` and `.cursor/rules/`. |
| `pirlruc/methodologies` | Cited by tag in docs (`tree/1.5.0/github-issue-adr`). Not a submodule. |

Android client analogs (payload shape, not Gradle layout): [pirlruc/finsilo](https://github.com/pirlruc/finsilo) (`:app` / `:domain`) and Heimdall (`app → kit → core`). Phone/camera JSON maps to Android `Build`, `ActivityManager`, `DisplayMetrics`, and Camera2 — see field descriptions on `app/device_models.py`. Do not copy Heimdall's native kit layout into this Python service.

## github-issue-adr

Authored backlog: [`docs/issues.yml`](issues.yml). Targets: [`docs/issues-sync-targets.yml`](issues-sync-targets.yml). Deviations (none): [`docs/guardrail-deviations.yml`](guardrail-deviations.yml). Do not invent `approved_by`.

```bash
bash scripts/setup-issue-scaffold.sh
bash scripts/issues-sync.sh --repo pirlruc/pixeldive --yaml docs/issues.yml --dry-run
bash scripts/sync-templates.sh
```

Issue content lives only in `docs/issues.yml`. Changing an `id` orphans the GitHub issue. Do not `gh issue create` by hand.

## Android payload contract

Clients should send the same keys they already read on-device:

| JSON object | Android source |
| --- | --- |
| `phone_info` | `android.os.Build` (`MANUFACTURER`, `MODEL`, `BRAND`, `DEVICE`, `BOARD`, `VERSION.RELEASE`, `VERSION.SDK_INT`) |
| `phone_capabilities` | `ActivityManager.MemoryInfo`, `isLowRamDevice()`, `Build.SUPPORTED_ABIS`, `Runtime.availableProcessors()`, `DisplayMetrics` |
| `camera_capabilities` | Camera2 `CameraManager` / `CameraCharacteristics` (`camera_count` must equal `len(cameras)`) |

## Known pitfalls

- `Session.metadata` cannot be a SQLAlchemy attribute name; the column is `metadata` mapped as `extra_metadata` with alias `metadata`.
- SQLite tests need `PRAGMA foreign_keys=ON` (enabled in `app/database.py` for sqlite URLs).
- Generated gRPC stubs live in `app/pb/` and are regenerated by `scripts/generate_proto.sh`.
- Private analog repos 404 without a PAT; quality gates then use `config/python.profile.thresholds.yml`.
- Alembic lives in `migrations/` (not `alembic/`) so the directory does not shadow the `alembic` package.
- Host may lack `python3-venv` / `ensurepip`; use `pip install --target .venv` or `--prefix .venv` and `scripts/python-env.sh` (Debian dist-packages under `.venv/local`). `pip-audit` uses `--no-deps --disable-pip` so it does not create a throwaway venv.
- SQLAlchemy relationships on `Session.images` must not use `from __future__ import annotations` on `app/models.py` (the annotation string is otherwise treated as a class name).
- PY-CPLX-002 averages **per-file** radon MI; large modules must stay split so min MI ≥ 40 and avg MI ≥ 70.
- PY-CPLX-001 max CC is **8** (guardrails 1.6.0). Prefer a shared helper over copying a wrapper into a new file.
- Dependabot grouped PRs can be stale vs `aiobotocore` (they may still list `boto3`) and may jump the Docker image to CPython 3.14. Runtime is **3.13** per PY-RUN-003 ([QUAL-002](issues.yml)); 3.14 re-evaluation is 2027-04. boto3 is not a dependency.
- Compose `depends_on.minio.required: false` needs Compose spec support for profiles; default `docker compose up` must stay local-disk.
- Host ports are `127.0.0.1` (DOCKER-COMPOSE-006). MinIO server image is scratch — no in-container HTTP healthcheck.
- `ENVIRONMENT=production` requires `AUTH_REQUIRED=true` and `GRPC_INSECURE=false`.
- Host-native HTTP/gRPC defaults are `127.0.0.1`; image/Compose set `0.0.0.0` in-container.

## Suggested next work

- [TOOL-002](issues.yml) publish GitHub issues from `docs/issues.yml`
- [QUAL-003](issues.yml) hadolint, KICS, Trivy/SBOM, uv.lock, MinIO digest pins
- [SEC-004](issues.yml) shared quota store on PostgreSQL (first multi-replica tests)
- [SEC-005](issues.yml) optional Redis quota hot path if Postgres contends
- Propose [docs/new-guardrails](new-guardrails/README.md) IDs upstream to pirlruc/guardrails

## Recent history

- Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1) (`c1eda05`)
- Phase 2 + SDK-001 + PERF-002 shipped in [PR #7](https://github.com/pirlruc/pixeldive/pull/7) (`96192bf`)
- Phase 3 remaining hardening in [PR #9](https://github.com/pirlruc/pixeldive/pull/9)
- Analog pins 1.6.0 / 1.5.0, DRY, bandit/pip-audit, production fail-closed (this branch)

*Last updated: 2026-09-20*
