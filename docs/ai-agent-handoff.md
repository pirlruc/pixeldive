# AI Agent Handoff — pixeldive

## Identity

| Field | Value |
| --- | --- |
| **Service** | pixeldive |
| **Type** | Async Python microservice (FastAPI REST + gRPC) for image-processing sessions |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/new-guardrails/` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Phase 1 session platform is **on main** ([PR #1](https://github.com/pirlruc/pixeldive/pull/1), merged 2026-09-19). Phase 2 hardening, Python SDK, capture demo, and async S3 (PERF-002) are **on main** ([PR #7](https://github.com/pirlruc/pixeldive/pull/7), merged 2026-09-19). Phase 3 remaining hardening is **on main** ([PR #9](https://github.com/pirlruc/pixeldive/pull/9)). Analog pins, DRY, and 1.6.0 QUAL-003 gates (hadolint, KICS, uv.lock, Trivy/SBOM, pydoclint) are **on main** ([PR #10](https://github.com/pirlruc/pixeldive/pull/10)). iOS SDK + SwiftUI demo (SDK-002) and Android SDK + Compose demo (SDK-003) are **on main** ([PR #12](https://github.com/pirlruc/pixeldive/pull/12); iOS opened as [PR #11](https://github.com/pirlruc/pixeldive/pull/11)). Camera-session ingest (PERF-005), streaming file uploads (SDK-004), mobile gRPC image clients (SDK-005), and camera-feed demos (SDK-006) shipped in [PR #13](https://github.com/pirlruc/pixeldive/pull/13). HTTP TLS + shared PEM with gRPC (SEC-007) is **on main** ([PR #14](https://github.com/pirlruc/pixeldive/pull/14), `78b0baa`). Upload measurement, batch/metadata caps, and production quotas (SEC-008), the `app` package split, and streamed demo uploads (PERF-006) are on this branch.

GitHub Epic/Task issues are not published ([TOOL-002](issues.yml)); statuses live in [`docs/issues.yml`](issues.yml).

| Module | Path | Notes |
| --- | --- | --- |
| kernel | `app/` root | Config, models, schemas, database, runtime, lifecycle, TLS files, `pb/`. No compatibility shims for old flat imports |
| sessions | `app/sessions/` | `service.py` plus batch/list/ops; in-process `quotas.py` (SEC-004 is the shared store) |
| REST | `app/rest/` | FastAPI `/api/v1` + `/health` `/ready` `/metrics` (`api.py`, `api_images.py`) |
| gRPC | `app/rpc/`, `proto/session_service.proto` | aio servicer; unary RPCs share `run_unary` |
| blobs | `app/blobs/` | SHA-256 local FS, spool, async S3 multipart |
| TLS | `app/tls_files.py`, `app/rest/http_tls.py`, `app/rpc/grpc_tls.py`, `app/ready_probe.py` | Shared PEM resolution; HTTP uvicorn SSLContext; gRPC server creds; HEALTHCHECK |
| errors | `app/error_map.py` | One exception → HTTP/gRPC table |
| lifecycle | `app/lifecycle.py`, `main.py` | Coordinated HTTP/gRPC stop, storage `aclose`, optional orphan sweep |
| SDK | `sdk/pixeldive_sdk/` | Flat package, `rest_*` / `grpc_*` prefixes. Public exports stay `RestClient`, `GrpcClient`, `sample_session_payload` |
| iOS SDK | `ios/` | Swift 6 SPM `PixeldiveSDK` (`PixeldiveClient` + `PixeldiveGrpcClient`) + SwiftUI camera demo |
| Android SDK | `android/` | Kotlin JVM `PixeldiveClient` + `PixeldiveGrpcClient` (OkHttp h2c) + Compose CameraX demo |
| demo | `demo/` | FastAPI UI; REST sessions, gRPC image bytes via `DemoClients` (`PIXELDIVE_TLS_CA`, `PIXELDIVE_GRPC_TARGET`) |
| runner | `main.py` | Uvicorn + grpc.aio on one asyncio loop |

Radon on 2026-09-21 (product gate: max CC 8, avg CC 2.11, min MI 46.02, avg MI 71.23). `scripts/` is outside that gate.

| Group | Files | Avg MI | Min MI | Max CC |
| --- | --- | --- | --- | --- |
| `app/rest` | 7 | 79.4 | 46.0 (`api_images.py`) | 7 |
| `app/rpc` | 16 | 73.7 | 53.0 (`grpc_image_rpcs.py`) | 8 (`update_patch`) |
| `app/blobs` | 26 | 71.7 | 48.8 (`s3_listing.py`) | 7 |
| `demo` | 9 | 71.7 | 47.0 (`clients.py`) | 4 |
| `sdk` gRPC | 9 | 69.9 | 47.8 (`grpc_client.py`) | 8 (`update_session_request`) |
| `app` kernel | 22 | 68.8 | 46.3 (`settings_runtime.py`) | 7 |
| `sdk` REST | 4 | 67.3 | 51.0 (`rest_http.py`) | 3 |
| `app/sessions` | 12 | 63.6 | 49.1 (`pagination.py`) | 6 |
| `scripts` | 9 | 52.3 | 30.4 (`lint-doc-links.py`) | 27 |

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
- PY-CPLX-002 averages **per-file** radon MI; large modules must stay split so min MI ≥ 40 and avg MI ≥ 70. Moving files does not change a file's MI. New `__init__.py` modules raise the average only when their own MI is high. `app/sessions/` is the dense product group; do not fold helpers back into `runtime.py` or `spool_writer.py`.
- PY-CPLX-001 max CC is **8** (guardrails 1.6.0). Prefer a shared helper over copying a wrapper into a new file.
- Dependabot grouped PRs can be stale vs `aiobotocore` (they may still list `boto3`) and may jump the Docker image to CPython 3.14. Runtime is **3.13** per PY-RUN-003 ([QUAL-002](issues.yml)); 3.14 re-evaluation is 2027-04. boto3 is not a dependency.
- Compose `depends_on.minio.required: false` needs Compose spec support for profiles; default `docker compose up` must stay local-disk.
- Host ports are `127.0.0.1` (DOCKER-COMPOSE-006). MinIO server uses `mc ready local` (quay image includes `mc`). `minio-init` is a one-shot job.
- Compose secrets have no in-file defaults; `cp .env.example .env` before `docker compose up`.
- `ENVIRONMENT=production` requires `AUTH_REQUIRED=true`, `HTTP_INSECURE=false`, `GRPC_INSECURE=false`, resolvable TLS cert/key files, and positive `RATE_LIMIT_PER_MINUTE`, `TENANT_MAX_UPLOAD_BYTES`, and `SESSION_MAX_UPLOAD_BYTES` (0 stays unlimited outside production).
- Host-native HTTP/gRPC defaults are `127.0.0.1`; image/Compose set `0.0.0.0` in-container.
- `GrpcClient` TLS PEMs require `insecure=False`; IP targets may need `ssl_target_name_override`.
- HTTP mTLS HEALTHCHECK needs `HTTP_TLS_CLIENT_CERT_FILE` / `HTTP_TLS_CLIENT_KEY_FILE` (compose comment documents a read-only `/certs` mount).
- Linux `scripts/ci-local.sh` skips `swift test` unless Swift is on PATH (SWIFT-ENV-001) and skips Gradle unless Java is on PATH (KT-ENV-001). When those tools are present, coverage is fail-closed (llvm-cov / Kover). `check-swift-coverage.py` puts `llvm-cov` next to `swift` on PATH and invokes `xcrun`/`llvm-cov` as literal argv (Semgrep `dangerous-subprocess-use-tainted-env-args`). `ios-sdk` on macOS sets `PIXELDIVE_REQUIRE_SWIFT=1`; `android-sdk` sets `PIXELDIVE_REQUIRE_JAVA=1`. Linux URLSession ignores `URLProtocol`; tests use `HTTPPerforming` plus a loopback server. FoundationNetworking has no `URLResponse()` and `uploadTask(fromFile:)` traps in `_BodyFileSource` — Linux loads the file into `httpBody`. Do not include the Compose demo from `ANDROID_HOME`. Apple Swift treats CRLF as one `Character`; sanitizers walk `unicodeScalars`. PNG multipart bodies are not UTF-8.
- Camera sessions should reuse one `PixeldiveClient` / gRPC channel, send in-memory frames (already in RAM from the camera), and use file/path helpers for gallery or on-disk bursts. Local storage hardlinks spools; S3 still streams multipart. Do not bump session rows after the first frame. Close `PixeldiveGrpcClient` when the host/token changes (`NioGrpcStreaming.close` / OkHttp dispatcher shutdown). Mobile gRPC is h2c: Android OkHttp `H2_PRIOR_KNOWLEDGE`, iOS grpc-swift NIO (Apple-only SPM product). URLSession does not speak h2c. Demos capture live camera (AVCapture / CameraX / getUserMedia) and upload on gRPC; session CRUD stays REST (`PIXELDIVE_GRPC_TARGET`, default `127.0.0.1:50051`). Native demos must not `listSessions` after every JPEG. The Python gRPC demo reads the multipart body once into a capped chunk list and streams those chunks ([PERF-006](issues.yml)); the REST-only fallback still uses a temp file. Starlette may still spool the multipart body. Raising inside the gRPC request iterator cancels the RPC, so the cap is enforced before `UploadImage`. TLS gRPC and Struct metadata are [SDK-007](issues.yml). ios-sdk Trivy scans `ios/` but must skip `.build` — grpc-swift / swift-nio-ssl checkouts ship sample private keys that fail SWIFT-SEC-004.
- Android `HttpUrl.resolve` dropped a base path prefix — concatenate like iOS/httpx. Multipart `Content-Type` parameters (`charset=`) must be stripped, not glued onto the subtype. iOS must trim bearer tokens, reject non-file upload URLs, refuse off-origin followed redirects, and must not fabricate sample cameras when discovery is empty.

## Suggested next work

- [TOOL-002](issues.yml) publish GitHub issues from `docs/issues.yml`
- [SEC-004](issues.yml) shared quota store on PostgreSQL (`app/sessions/quotas.py`; first multi-replica tests). In-process `TenantQuota` is still sync
- S3 put-skip is process-local and cleared on `delete`; replicas still re-PUT until SEC-004
- [SDK-007](issues.yml) TLS gRPC constructors + protobuf Struct metadata on mobile
- [SEC-005](issues.yml) optional Redis quota hot path if Postgres contends
- [SDK-008](issues.yml) iOS/Android custom CA trust for private PKI
- First image/GitHub Release publish: SC-SIGN-001, SC-PROV-001, DOCKER-TEST-001
- Propose [docs/new-guardrails](new-guardrails/README.md) IDs upstream to pirlruc/guardrails (including [swift.md](new-guardrails/swift.md) and [kotlin.md](new-guardrails/kotlin.md))

## Recent history

- Phase 1 + REV-001 shipped in [PR #1](https://github.com/pirlruc/pixeldive/pull/1) (`c1eda05`)
- Phase 2 + SDK-001 + PERF-002 shipped in [PR #7](https://github.com/pirlruc/pixeldive/pull/7) (`96192bf`)
- Phase 3 remaining hardening in [PR #9](https://github.com/pirlruc/pixeldive/pull/9)
- Analog pins 1.6.0 / 1.5.0, DRY, QUAL-003 1.6.0 gates ([PR #10](https://github.com/pirlruc/pixeldive/pull/10))
- SDK-002 + SDK-003 shipped in [PR #12](https://github.com/pirlruc/pixeldive/pull/12) (iOS opened as [PR #11](https://github.com/pirlruc/pixeldive/pull/11)): Swift `PixeldiveSDK` + SwiftUI demo; Kotlin `PixeldiveClient` + Compose demo; Swift/Kotlin proposals in `docs/new-guardrails/`
- Review pass: 3xx/redirect + multipart filename hardening; llvm-cov/Kover/ktlint/detekt fail-closed in CI
- Follow-up pass: Android base-path join, media-type parameters, cancellable OkHttp; iOS token trim, file URL, off-origin redirect refuse, empty camera discovery
- SEC-007: HTTP TLS + shared `TLS_*` PEM files; production fail-closed for HTTP and gRPC; Python SDK custom CA; Docker HEALTHCHECK `ready_probe` ([PR #14](https://github.com/pirlruc/pixeldive/pull/14))
- SEC-008: measured upload size, REST batch cap before spool, metadata cap, production quotas, shared gRPC ingest abort, process-local S3 put skip, demo temp-file upload
- Package split: `app/rest`, `app/rpc`, `app/blobs`, `app/sessions`; filenames kept; no shims. PERF-006: gRPC demo streams a capped chunk list. Mobile `decodeUpload` / `decodeBatch` share one field-1 collector
- Camera ingest: unified `add_image`/`add_images_batch`, local spool hardlink, parallel REST spool, quota release on delete, streaming mobile file uploads ([PERF-005](issues.yml), [SDK-004](issues.yml))
- Mobile gRPC image clients + camera-feed demos ([SDK-005](issues.yml), [SDK-006](issues.yml)): hand-rolled protobuf, iOS grpc-swift NIO, Android OkHttp h2c, AVCapture/CameraX/getUserMedia → `UploadImage`
- Follow-up: ruff format on `tests/test_sdk.py`; close gRPC channels on cache replace; skip REST list and JPEG encode while a frame is in flight; NIO call timeout; percent-decode `grpc-message`; Python Struct metadata ([PR #13](https://github.com/pirlruc/pixeldive/pull/13))

*Last updated: 2026-09-21*
