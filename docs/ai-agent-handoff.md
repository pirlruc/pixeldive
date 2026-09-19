# AI Agent Handoff — pixeldive

## Identity

| Field | Value |
| --- | --- |
| **Service** | pixeldive |
| **Type** | Async Python microservice (FastAPI REST + gRPC) for image-processing sessions |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.2.0/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Phase 1 session platform is **on main** ([PR #1](https://github.com/pirlruc/pixeldive/pull/1), merged 2026-09-19). Phase 2 hardening, Python SDK, capture demo, and async S3 (PERF-002) live on this branch: bearer auth + gRPC TLS options, spool+digest ingest, cursor pagination, Alembic under `migrations/`, race-aware GC, `/ready` + `/metrics`, `pixeldive_sdk`, `python -m demo`, and a lazy aiobotocore adapter. Analog submodule pins ([TOOL-001-T1](issues.yml)) still need a token that can clone private `pirlruc/guardrails` and `pirlruc/github-scaffold`. GitHub Epic/Task issues are not published ([TOOL-002](issues.yml)); statuses live in [`docs/issues.yml`](issues.yml).

| Module | Path | Notes |
| --- | --- | --- |
| models | `app/models.py`, `app/schemas.py` | SQLModel tables + Android-aligned JSON payloads; `storage_path` is internal |
| service | `app/service.py` | Single business layer for REST and gRPC (mixins for list/ingest/batch) |
| REST | `app/api.py`, `app/api_images.py` | FastAPI `/api/v1` + `/health` `/ready` `/metrics` |
| gRPC | `app/grpc_server.py`, `proto/session_service.proto` | aio servicer; generated stubs in `app/pb/` |
| storage | `app/local_storage.py`, `app/s3_storage.py`, `app/s3_client.py` | SHA-256 local FS + async S3 adapter (aiobotocore) |
| SDK | `sdk/pixeldive_sdk/` | `RestClient` + `GrpcClient` |
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

CI: `.github/workflows/quality.yml`, `security.yml`. Actions are SHA-pinned. Numeric gates read analog `docs/guardrails/python/profile.thresholds.yml` after `scripts/ci-init-guardrails.sh` (`GUARDRAILS_READ_TOKEN`); otherwise the consumer copy `config/python.profile.thresholds.yml`. Do not clone `.github/scaffold` in CI.

Demo against a running service:

```bash
PYTHONPATH=sdk:. PIXELDIVE_BASE_URL=http://127.0.0.1:8000 python3 -m demo
```

## Analog pins (TOOL-001)

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Intended Git submodule at `docs/guardrails/` (tag **1.3.0**). Private; needs `GUARDRAILS_READ_TOKEN`. |
| `pirlruc/github-scaffold` | Intended Git submodule at `.github/scaffold/` (tag **1.2.0**). Templates are synced into `.github/` and `.cursor/rules/`. |
| `pirlruc/methodologies` | Cited by tag in docs (`tree/1.2.0/github-issue-adr`). Not a submodule. |

Android client analogs (payload shape, not Gradle layout): [pirlruc/finsilo](https://github.com/pirlruc/finsilo) (`:app` / `:domain`) and Heimdall (`app → kit → core`). Phone/camera JSON maps to Android `Build`, `ActivityManager`, `DisplayMetrics`, and Camera2 — see field descriptions on `app/device_models.py`. Do not copy Heimdall's native kit layout into this Python service.

## github-issue-adr

Authored backlog: [`docs/issues.yml`](issues.yml). Targets: [`docs/issues-sync-targets.yml`](issues-sync-targets.yml). Deviations (none): [`docs/guardrail-deviations.yml`](guardrail-deviations.yml). Do not invent `approved_by`.

```bash
bash scripts/setup-issue-scaffold.sh
bash scripts/issues-sync.sh --repo pirlruc/pixeldive --yaml docs/issues.yml --dry-run
bash scripts/sync-templates.sh
```

Issue content lives only in `docs/issues.yml`. Changing an `id` orphans the GitHub issue. Do not `gh issue create` by hand.

GitHub issue publish needs Issues: Read and write ([TOOL-002](issues.yml)). Until then, keep the manifest as the decision log. Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1); Phase 2 + SDK-001 + PERF-002 are `status: done` in the YAML on this branch.

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
- Host Python may lack `ensurepip`; use `pip install --target .venv` and `PYTHONPATH=.venv`.
- SQLAlchemy relationships on `Session.images` must not use `from __future__ import annotations` on `app/models.py` (the annotation string is otherwise treated as a class name).
- PY-CPLX-002 averages **per-file** radon MI; large modules must stay split so min MI ≥ 40 and avg MI ≥ 70.

## Suggested next work

- [TOOL-001-T1](issues.yml) pin analog submodules once tokens exist
- [TOOL-002](issues.yml) publish GitHub issues from `docs/issues.yml`
- [SEC-002](issues.yml) per-tenant rate limits and upload quotas
- [SEC-003](issues.yml) hide other tenants' session existence
- [API-003](issues.yml) GrpcClient parity with RestClient
- [PERF-003](issues.yml) multipart S3 PUT (O(chunk) save_file)
- [PERF-004](issues.yml) chunked SDK uploads
- [OPS-002](issues.yml) coordinated dual-server shutdown
- [OPS-003](issues.yml) MinIO Compose profile
- [DATA-003](issues.yml) PostgreSQL CI job
- [DATA-004](issues.yml) schedule orphan sweeper in-process

## Recent history

- Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1) (`c1eda05`)
- `docs(issues): record PR #1 ship on Phase 1 and REV-001` (`a7e8ee2`)
- This branch: Phase 2 (SEC/PERF/DATA/OPS/API), SDK-001, demo app, PERF-002 async S3; PY-* gates held without `docs/guardrail-deviations.yml` entries

*Last updated: 2026-09-19*
