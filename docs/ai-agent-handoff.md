# AI Agent Handoff — pixeldive

## Identity

| Field | Value |
| --- | --- |
| **Service** | pixeldive |
| **Type** | Async Python microservice (FastAPI REST + gRPC) for image-processing sessions |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/new-guardrails/` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Phase 1 session platform is **on main** ([PR #1](https://github.com/pirlruc/pixeldive/pull/1), merged 2026-09-19). Phase 2 hardening, Python SDK, capture demo, and async S3 (PERF-002) are **on main** ([PR #7](https://github.com/pirlruc/pixeldive/pull/7), merged 2026-09-19). Phase 3 remaining hardening is **on main** ([PR #9](https://github.com/pirlruc/pixeldive/pull/9)). Analog pins, DRY, and 1.6.0 QUAL-003 gates (hadolint, KICS, uv.lock, Trivy/SBOM, pydoclint) are on this branch.

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
| iOS SDK | `ios/` | Swift 6 SPM `PixeldiveSDK` (`PixeldiveClient`) + SwiftUI demo |
| Android SDK | `android/` | Kotlin JVM `PixeldiveClient` + Compose demo (`:demo` when `local.properties` or `PIXELDIVE_INCLUDE_ANDROID_DEMO=1`) |
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

CI: `.github/workflows/quality.yml` (SQLite PY-* plus `postgres`, `docker-lint`, `uv-lock`, `ios-sdk` on macOS, `android-sdk` on Ubuntu JDK 21), `security.yml` (gitleaks, CodeQL, bandit, pip-audit, semgrep `p/python` + `p/swift` + `p/kotlin`, dependency-review, Trivy, SBOM). Actions are SHA-pinned. Numeric gates read analog `docs/guardrails/python/profile.thresholds.yml` after `scripts/ci-init-guardrails.sh` (`GUARDRAILS_READ_TOKEN`); otherwise the consumer copy `config/python.profile.thresholds.yml`. Swift overlays live in `config/swift.profile.thresholds.yml` and are enforced by llvm-cov + `scripts/check-swift-docs.py`. Kotlin overlays live in `config/kotlin.profile.thresholds.yml` and are enforced by Kover/ktlint/detekt. The overlay reader allows stricter consumer values and fails on looser ones. Do not clone `.github/scaffold` in CI.

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

## Android / iOS payload contract

Clients should send the same keys they already read on-device. iOS maps into those
keys rather than forking the schema ([SDK-002](issues.yml)).

| JSON object | Android source | iOS source |
| --- | --- | --- |
| `phone_info` | `android.os.Build` (`MANUFACTURER`, `MODEL`, `BRAND`, `DEVICE`, `BOARD`, `VERSION.RELEASE`, `VERSION.SDK_INT`) | `UIDevice` / `utsname`; `android_version` and `sdk_int` carry the iOS version string and major int |
| `phone_capabilities` | `ActivityManager.MemoryInfo`, `isLowRamDevice()`, `Build.SUPPORTED_ABIS`, `Runtime.availableProcessors()`, `DisplayMetrics` | `ProcessInfo.physicalMemory`, `processorCount`, `UIScreen` |
| `camera_capabilities` | Camera2 `CameraManager` / `CameraCharacteristics` (`camera_count` must equal `len(cameras)`) | `AVCaptureDevice.DiscoverySession` |
| `metadata.platform` | `"android"` from `DeviceSnapshot` | `"ios"` from `DeviceSnapshot` |

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
- Host ports are `127.0.0.1` (DOCKER-COMPOSE-006). MinIO server uses `mc ready local` (quay image includes `mc`). `minio-init` is a one-shot job.
- Compose secrets have no in-file defaults; `cp .env.example .env` before `docker compose up`.
- `ENVIRONMENT=production` requires `AUTH_REQUIRED=true` and `GRPC_INSECURE=false`.
- Host-native HTTP/gRPC defaults are `127.0.0.1`; image/Compose set `0.0.0.0` in-container.
- Linux `scripts/ci-local.sh` skips `swift test` unless Swift is on PATH (SWIFT-ENV-001) and skips Gradle unless Java is on PATH (KT-ENV-001). When those tools are present, coverage is fail-closed (llvm-cov / Kover), not a log-only echo. `check-swift-coverage.py` finds `llvm-cov` next to `swift` when it is not on PATH. The `ios-sdk` job on macOS sets `PIXELDIVE_REQUIRE_SWIFT=1` (SwiftLint + `xcodebuild` + Trivy `fs`). The `android-sdk` job sets `PIXELDIVE_REQUIRE_JAVA=1` (ktlint + detekt + Kover + Trivy `fs`). Ubuntu `quality` has Swift and Java and runs both package tests. Linux URLSession ignores `URLProtocol`; iOS client tests use an `HTTPPerforming` stub and a loopback POSIX server for the real URLSession path. FoundationNetworking has no `URLResponse()` — use `URLResponse(url:mimeType:expectedContentLength:textEncodingName:)`. Android client tests use OkHttp MockWebServer. Do not include the Compose demo from `ANDROID_HOME` — GitHub Ubuntu sets that; use `local.properties` or `PIXELDIVE_INCLUDE_ANDROID_DEMO=1`. Default URLSession/OkHttp clients do not follow redirects (Authorization leak). Apple Swift treats CRLF as one `Character`; multipart sanitizers must walk `unicodeScalars` so CR and LF are each stripped. PNG multipart bodies are not UTF-8 — assert on `Data`, not `String(encoding:)`. Proposed analog changes: Foundation-only SPM and JVM `:sdk` tests on Linux ([docs/new-guardrails](new-guardrails/)).

## Suggested next work

- [TOOL-002](issues.yml) publish GitHub issues from `docs/issues.yml`
- [SEC-004](issues.yml) shared quota store on PostgreSQL (first multi-replica tests)
- [SEC-005](issues.yml) optional Redis quota hot path if Postgres contends
- First image/GitHub Release publish: SC-SIGN-001, SC-PROV-001, DOCKER-TEST-001
- Propose [docs/new-guardrails](new-guardrails/README.md) IDs upstream to pirlruc/guardrails (including [swift.md](new-guardrails/swift.md) and [kotlin.md](new-guardrails/kotlin.md))

## Recent history

- Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1) (`c1eda05`)
- Phase 2 + SDK-001 + PERF-002 shipped in [PR #7](https://github.com/pirlruc/pixeldive/pull/7) (`96192bf`)
- Phase 3 remaining hardening in [PR #9](https://github.com/pirlruc/pixeldive/pull/9)
- Analog pins 1.6.0 / 1.5.0, DRY, QUAL-003 1.6.0 gates ([PR #10](https://github.com/pirlruc/pixeldive/pull/10))
- SDK-002: Swift `PixeldiveSDK` + SwiftUI demo + Swift guardrail proposals
- SDK-003: Kotlin `PixeldiveClient` + Compose demo + Kotlin/Android guardrail proposals
- Review pass: 3xx/redirect + multipart filename hardening; llvm-cov/Kover/ktlint/detekt fail-closed in CI

*Last updated: 2026-09-20*
