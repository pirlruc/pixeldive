# AI Agent Handoff — pixeldive

## Identity

| Field | Value |
| --- | --- |
| **Service** | pixeldive |
| **Type** | Async Python microservice (FastAPI REST + gRPC) for image-processing sessions |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.2.0/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Phase 1 session platform is **on main** ([PR #1](https://github.com/pirlruc/pixeldive/pull/1), merged 2026-09-19). Phase 2 hardening, Python SDK, capture demo, and async S3 (PERF-002) are **on main** ([PR #7](https://github.com/pirlruc/pixeldive/pull/7), merged 2026-09-19). Phase 3 remaining hardening (quotas, uniform 404, GrpcClient parity, S3 multipart, SDK path uploads, coordinated shutdown, MinIO profile, Postgres CI, orphan sweep) is in flight on this branch.

Analog submodule pins ([TOOL-001-T1](issues.yml)) still need a token that can clone private `pirlruc/guardrails` and `pirlruc/github-scaffold`. GitHub Epic/Task issues are not published ([TOOL-002](issues.yml)); statuses live in [`docs/issues.yml`](issues.yml).

| Module | Path | Notes |
| --- | --- | --- |
| models | `app/models.py`, `app/schemas.py` | SQLModel tables + Android-aligned JSON payloads; `storage_path` is internal |
| service | `app/service.py` | Single business layer for REST and gRPC (mixins for list/ingest/batch) |
| quotas | `app/quotas.py` | In-process per-tenant rate/byte caps (SEC-002); shared store is SEC-004 |
| REST | `app/api.py`, `app/api_images.py` | FastAPI `/api/v1` + `/health` `/ready` `/metrics` |
| gRPC | `app/grpc_server.py`, `proto/session_service.proto` | aio servicer; generated stubs in `app/pb/` |
| storage | `app/local_storage.py`, `app/s3_storage.py`, `app/s3_multipart.py` | SHA-256 local FS + async S3 multipart PUT |
| lifecycle | `app/lifecycle.py`, `main.py` | Coordinated HTTP/gRPC stop, storage `aclose`, optional orphan sweep |
| SDK | `sdk/pixeldive_sdk/` | `RestClient` + `GrpcClient` (session/image parity, path uploads) |
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

CI: `.github/workflows/quality.yml` (`quality` SQLite PY-* plus `postgres` Alembic job), `security.yml`. Actions are SHA-pinned. Numeric gates read analog `docs/guardrails/python/profile.thresholds.yml` after `scripts/ci-init-guardrails.sh` (`GUARDRAILS_READ_TOKEN`); otherwise the consumer copy `config/python.profile.thresholds.yml`. Do not clone `.github/scaffold` in CI.

Demo against a running service:

```bash
PYTHONPATH=sdk:. PIXELDIVE_BASE_URL=http://127.0.0.1:8000 python3 -m demo
```

S3 Compose profile:

```bash
STORAGE_BACKEND=s3 bash scripts/compose-s3.sh
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

GitHub issue publish needs Issues: Read and write ([TOOL-002](issues.yml)). Until then, keep the manifest as the decision log. Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1); Phase 2 + SDK-001 + PERF-002 shipped in [PR #7](https://github.com/pirlruc/pixeldive/pull/7).

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
- Host Python may lack `ensurepip`; use `pip install --target .venv` or `--prefix .venv` and `scripts/python-env.sh` (Debian dist-packages under `.venv/local`).
- SQLAlchemy relationships on `Session.images` must not use `from __future__ import annotations` on `app/models.py` (the annotation string is otherwise treated as a class name).
- PY-CPLX-002 averages **per-file** radon MI; large modules must stay split so min MI ≥ 40 and avg MI ≥ 70.
- Dependabot grouped PRs can be stale vs `aiobotocore` (they may still list `boto3`) and may jump the Docker image to CPython 3.14. Runtime is **3.13** per PY-RUN-003 ([QUAL-002](issues.yml)); 3.14 re-evaluation is 2027-04. boto3 is not a dependency.
- Compose `depends_on.minio.required: false` needs Compose spec support for profiles; default `docker compose up` must stay local-disk.

## Suggested next work

- [TOOL-001-T1](issues.yml) pin analog submodules once tokens exist
- [TOOL-002](issues.yml) publish GitHub issues from `docs/issues.yml`
- [SEC-004](issues.yml) shared quota store across replicas (recommend Postgres)
- Close stale per-ecosystem Dependabot PRs after the grouped-compatible bump lands (SC-DEP-002)

## Recent history

- Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1) (`c1eda05`)
- `docs(issues): record PR #1 ship on Phase 1 and REV-001` (`a7e8ee2`)
- Phase 2 (SEC/PERF/DATA/OPS/API), SDK-001, demo, PERF-002 async S3 shipped in [PR #7](https://github.com/pirlruc/pixeldive/pull/7) (`96192bf`)
- Phase 3 remaining hardening + compatible Dependabot updates on `cursor/phase3-hardening-deps-7b15`
- QUAL-002: CPython 3.13 per PY-RUN-003 (not Dependabot 3.14); boto3 stays replaced by aiobotocore

*Last updated: 2026-09-20*
