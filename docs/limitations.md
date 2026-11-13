# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`,
which has no entries).

| Limit | Why |
| --- | --- |
| Analog submodules need a PAT to clone | `pirlruc/guardrails` @ 1.15.0 and `pirlruc/github-scaffold` @ 1.12.0 are private gitlinks. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set. `scripts/check-submodule-pins.sh` checks the gitlink without cloning. |
| GitHub issues not published | Issue create is a publishing action. Tracked as [TOOL-002](issues.yml). |
| Tests use SQLite locally | Production is PostgreSQL + asyncpg. SQLite stays the unit-test default; CI job `postgres` is [DATA-003](issues.yml). |
| Auth is opt-in | `AUTH_REQUIRED` defaults to false so local tests and compose stay unauthenticated. Set `ENVIRONMENT=production` (requires `AUTH_REQUIRED`, `HTTP_INSECURE=false`, `GRPC_INSECURE=false`, resolvable TLS cert/key files, and positive rate/byte quotas) plus a PEM pair. Host-native HTTP/gRPC binds default to `127.0.0.1`; the image/Compose set `0.0.0.0` inside the container network. Docker HEALTHCHECK uses `127.0.0.1` and skips hostname checks; HTTP mTLS also needs `HTTP_TLS_CLIENT_CERT_FILE` / `HTTP_TLS_CLIENT_KEY_FILE` on the app container. |
| Quotas are per-process | [SEC-002](issues.yml) caps many phones on one replica. Shared accounting across app replicas is [SEC-004](issues.yml) (Postgres). Redis is [SEC-005](issues.yml) if that hot path contends. Session delete now returns reserved upload bytes in-process. |
| GC age window | `GC_MIN_AGE_SECONDS` defaults to 60. Set it explicitly when a deploy needs a different grace window ([DATA-004](issues.yml)). |
| Host may lack `python3-venv` | Use `pip install --target .venv` or `pip install --prefix .venv` (Debian: `.venv/local/...`). `scripts/python-env.sh` resolves both layouts. Do not install into the system OS. Local parity is `scripts/check-ci-local.sh`. `uv.lock` is the PY-RUN-001 source of truth. |
| Swift / Xcode not on Linux CI hosts | SWIFT-ENV-001 requires macOS for UIKit/`xcodebuild`. `scripts/check-ios-sdk.sh` skips when `swift` is missing unless `PIXELDIVE_REQUIRE_SWIFT=1`. When Swift is present it fail-closes llvm-cov (`SWIFT-TEST-002`) and public-API `///` docs (`SWIFT-DOC-001`). Linux `uploadTask(fromFile:)` traps in FoundationNetworking; the SDK loads the file into `httpBody` on that path. The `ios-sdk` job on `macos-15` also runs checksum-pinned SwiftLint, `xcodebuild` for the SPM scheme, and Trivy `fs`. Analog proposals: [new-guardrails/swift.md](new-guardrails/swift.md). |
| Android Compose demo is host-only | `:sdk` JVM tests, ktlint, detekt, and Kover run on Linux. The demo is included only with `local.properties` or `PIXELDIVE_INCLUDE_ANDROID_DEMO=1` (not `ANDROID_HOME`). Analog proposals: [new-guardrails/kotlin.md](new-guardrails/kotlin.md). |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.13.17-slim-trixie` ([QUAL-002](issues.yml), PY-RUN-003). 3.14 does not qualify until the 2027-04 re-evaluation. Multi-arch deploys need a manifest-list digest. |
| Compose secrets | `docker-compose.yml` interpolates passwords with no in-file defaults (DOCKER-COMPOSE-004). Copy `.env.example` to `.env` before `docker compose up`. `scripts/compose-s3.sh` still supplies local demo defaults. |
| Published image | Tag `0.1.0` is published. Do not move it. A later tag publishes through `container-publish`. |
