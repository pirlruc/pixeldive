# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`,
which has no entries).

| Limit | Why |
| --- | --- |
| Analog submodules need a PAT to clone | `pirlruc/guardrails` @ 1.6.0 and `pirlruc/github-scaffold` @ 1.5.0 are private gitlinks. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set. |
| GitHub issues not published | Issue create is a publishing action. Tracked as [TOOL-002](issues.yml). |
| Tests use SQLite locally | Production is PostgreSQL + asyncpg. SQLite stays the unit-test default; CI job `postgres` is [DATA-003](issues.yml). |
| Auth is opt-in | `AUTH_REQUIRED` defaults to false so local tests and compose stay unauthenticated. Set `ENVIRONMENT=production` (or `AUTH_REQUIRED` + TLS) for production; gRPC TLS is also explicit via `GRPC_INSECURE`. Host-native HTTP/gRPC binds default to `127.0.0.1`; the image/Compose set `0.0.0.0` inside the container network. |
| Quotas are per-process | [SEC-002](issues.yml) caps many phones on one replica. Shared accounting across app replicas is [SEC-004](issues.yml) (Postgres). Redis is [SEC-005](issues.yml) if that hot path contends. |
| GC age window defaults to 0 | `GC_MIN_AGE_SECONDS=0` skips the delete-time grace used to protect concurrent same-hash uploads. Set a positive value and `ORPHAN_SWEEP_INTERVAL_SECONDS` in production ([DATA-004](issues.yml)). |
| Host may lack `python3-venv` | Use `pip install --target .venv` or `pip install --prefix .venv` (Debian: `.venv/local/...`). `scripts/python-env.sh` resolves both layouts. Do not install into the system OS. `pip-audit` in `ci-local.sh` uses `--no-deps --disable-pip` so it does not spawn a throwaway venv. Hosts without `uv` still install from `requirements.txt`; `uv.lock` is the PY-RUN-001 source of truth. |
| Swift / Xcode not on Linux CI hosts | SWIFT-ENV-001 requires macOS for UIKit/`xcodebuild`. `scripts/check-ios-sdk.sh` skips when `swift` is missing unless `PIXELDIVE_REQUIRE_SWIFT=1`. When Swift is present it fail-closes llvm-cov (`SWIFT-TEST-002`) and public-API `///` docs (`SWIFT-DOC-001`). The `ios-sdk` job on `macos-15` also runs checksum-pinned SwiftLint, `xcodebuild` for the SPM scheme, and Trivy `fs`. Analog proposals: [new-guardrails/swift.md](new-guardrails/swift.md). |
| Android Compose demo is host-only | `:sdk` JVM tests, ktlint, detekt, and Kover run on Linux. The demo is included only with `local.properties` or `PIXELDIVE_INCLUDE_ANDROID_DEMO=1` (not `ANDROID_HOME`). Analog proposals: [new-guardrails/kotlin.md](new-guardrails/kotlin.md). |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.13.15-slim-bookworm` ([QUAL-002](issues.yml), PY-RUN-003). 3.14 does not qualify until the 2027-04 re-evaluation. Multi-arch deploys need a manifest-list digest. |
| Compose secrets | `docker-compose.yml` interpolates passwords with no in-file defaults (DOCKER-COMPOSE-004). Copy `.env.example` to `.env` before `docker compose up`. `scripts/compose-s3.sh` still supplies local demo defaults. |
| SC-SIGN / SC-PROV / DOCKER-TEST-001 | Apply to published artifacts. This repo has no registry or GitHub Release publish path yet. |
