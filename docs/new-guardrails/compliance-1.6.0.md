# Guardrails 1.6.0 compliance (pixeldive)

Pin: [pirlruc/guardrails](https://github.com/pirlruc/guardrails) **1.6.0** at
`docs/guardrails/`, [pirlruc/github-scaffold](https://github.com/pirlruc/github-scaffold)
**1.5.0** at `.github/scaffold/`. Methodology citations follow scaffold 1.5.0
([methodologies 1.5.0](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr)).

`docs/guardrail-deviations.yml` stays empty. Do not invent `approved_by`.
Gates that apply only to **published** artifacts (cosign, SLSA provenance,
container-structure-test) are not fake-passed; they start with the first
registry or GitHub Release publish.

## Python pack

| ID | Status |
|----|--------|
| PY-RUN-001 | CPython 3.13. Package manager is `uv` with committed `uv.lock`. `requirements.txt` is `uv export` (pip/Docker freeze); CI runs `uv lock --check` and `scripts/check-uv-export.sh`. |
| PY-RUN-002 / PY-QUAL-001 | ruff format+lint, mypy in `scripts/ci-local.sh`. `lint_exception_max_days: 14` is in the consumer copy; noqa entries are not yet time-boxed. |
| PY-RUN-003 | 3.13 until 2027-04 ([QUAL-002](../issues.yml)). |
| PY-CPLX-001 | Consumer `max_cyclomatic_complexity: 8` (org 1.6.0). |
| PY-CPLX-002 | min MI 40; **avg MI 70** (stricter than org 60). Overlay reader allows stricter, forbids looser. |
| PY-TEST-002 | 95/95 statement/branch. |
| PY-DOC-001 | interrogate 95. |
| PY-DOC-002 | ruff pydocstyle Google plus `pydoclint --style=google` (`scripts/run-pydoclint.py`). |
| PY-SEC-002 | bandit in `ci-local.sh` and `security.yml`; semgrep `p/python` ERROR in `security.yml`; CodeQL `security-extended` remains. |
| PY-SEC-003 | gitleaks 8.30.1 (aligned with pre-commit). |
| PY-SEC-004 | pip-audit in `ci-local.sh` and `security.yml` with `--no-deps --disable-pip` (pinned `requirements.txt`; no throwaway venv). |

## Docker / Compose

| ID | Status |
|----|--------|
| DOCKER-BUILD-001…005 | Multi-stage, slim, digest-pinned Python base, `.dockerignore`, no secrets in image. `requirements.txt` is the image lockfile (DOCKER-BUILD-004). |
| DOCKER-RUN-001…006 | UID 65532, exec ENTRYPOINT, HEALTHCHECK JSON CMD, compose `read_only` + cap_drop + no-new-privileges. |
| DOCKER-COMPOSE-001 | Postgres and MinIO (server + mc) digest-pinned with tag comments. |
| DOCKER-COMPOSE-002 | db, app, and MinIO server have restart + healthcheck. `minio-init` is a one-shot job (`service_completed_successfully`); KICS healthcheck ignore is in [scanner-exceptions.md](../scanner-exceptions.md). |
| DOCKER-COMPOSE-003 | Named volumes only. |
| DOCKER-COMPOSE-004 | Secrets come from `.env` (`cp .env.example .env`). Compose has no password literals. |
| DOCKER-COMPOSE-005 | App/MinIO drop ALL caps; Postgres drops ALL and adds back chown/gosu caps (KICS ignore documented). No `privileged`. |
| DOCKER-COMPOSE-006 | Host ports bound to `127.0.0.1`. |
| DOCKER-COMPOSE-007 | `mem_limit` on db, app, minio. |
| DOCKER-COMPOSE-008 | Volume backup notes in README. |
| DOCKER-LINT-001 | hadolint failure-threshold `warning` in CI and `scripts/run-hadolint.sh`. |
| DOCKER-LINT-002 | KICS fail-on `high,medium` in CI and `scripts/run-kics.sh`. |
| DOCKER-LINT-003 | `docker compose --profile s3 config --quiet` in CI. |
| DOCKER-SEC-001 | Trivy HIGH/CRITICAL on the CI-built `pixeldive:ci` image (`security.yml` `image` job). `ignore-unfixed` for Debian `will_not_fix`/`fix_deferred`; pip/setuptools stripped from the runtime image. |
| SC-SBOM-001/002 | CycloneDX JSON retained as a CI artifact from that image. |
| SC-SIGN-001 / SC-PROV-001 / DOCKER-TEST-001 | Apply to published artifacts. No registry publish path yet. |

## CI / supply chain / docs

| ID | Status |
|----|--------|
| CI-001…003, 005, 006, 008, 022, 025, 029 | SHA-pinned actions, concurrency, timeouts, High/Critical security fail, local parity, fail-closed thresholds, workflow `permissions:`, monthly security cron. |
| CI-012 | security.yml includes gitleaks, CodeQL, bandit, pip-audit, semgrep, dependency-review, Trivy, SBOM. |
| SC-DEP-001…003 | Dependabot seed includes github-actions, pip, docker, uv, pre-commit. |
| SC-DEP-004 | Gitlink SHA + annotated tags 1.6.0 / 1.5.0. |
| SHELL-LINT-001 | ShellCheck `--severity=error` in CI and `scripts/run-shellcheck.sh`. |
| DOC-LINT-001/002 | `scripts/lint-doc-links.py` (vendored analog copy; skips `.venv`). |

## Security exclusions (not reduced further)

`app/pb/`, `docs/guardrails/`, and `.github/scaffold` remain CodeQL `paths-ignore`
scope filters ([scanner-exceptions.md](../scanner-exceptions.md)). They are not
product findings. No finding-level `nosec` / CodeQL suppressions were added.

In-code hardenings in this bump: HMAC API-key compare, in-process quota lock,
magic-byte upload sniff, production `ENVIRONMENT` fail-closed, download no longer
double-hits quotas, S3 “missing” no longer treats any `ClientError` whose message
contains `404` as not-found. Host-native HTTP/gRPC defaults are `127.0.0.1` so
bandit B104 is not suppressed; the image and Compose still set `0.0.0.0` inside
the container network. HTTP TLS (SEC-007) closes the remaining plaintext REST
gap: production also requires `HTTP_INSECURE=false` and a PEM pair shared with
gRPC when per-transport files are unset.

## Swift pack (SDK-002)

The analog `swift/` pack applies to `ios/`. Consumer overlay:
`config/swift.profile.thresholds.yml` (statement coverage **95**, stricter than org 90).

CI jobs:

- `quality` (Ubuntu) runs `scripts/check-ios-sdk.sh` when `swift` is on PATH:
  `swift test --enable-code-coverage`, llvm-cov vs the overlay, and
  `scripts/check-swift-docs.py` vs `doc_coverage`.
- `ios-sdk` (`macos-15`, `PIXELDIVE_REQUIRE_SWIFT=1`) is fail-closed: same
  coverage/docs gates, checksum-pinned SwiftLint (`SWIFT-LINT-001`),
  `xcodebuild -scheme PixeldiveSDK -destination platform=macOS` (`SWIFT-LANG-002`),
  and Trivy filesystem scan of `ios/` (`SWIFT-SEC-004`; analog names
  osv-scanner/grype — Trivy is proposed as an accepted evaluator in
  [swift.md](swift.md)).

Proposed IDs that Kotlin already has (SWIFT-CPLX-001/002, SWIFT-CONC-001/002,
SWIFT-IOS-003/004, SWIFT-SEC-005, SWIFT-ENV-001 Linux SPM overlay) are in
[swift.md](swift.md), not in `docs/guardrail-deviations.yml`.

Gaps that remain (not recorded as deviations because they are analog-tooling
or host-only, not lowered numeric gates):

- SWIFT-ENV-002 SwiftFormat is not a pre-commit hook (in-repo `.swiftformat` exists).
- SWIFT-IOS-001 Xcode 26 is not asserted on `macos-15`.
- SwiftUI demo / `xcodebuild` for the demo app stays host-only.
- `LiveDevice` UIKit/AVFoundation paths compile only for iOS; macOS/Linux CI
  covers the ProcessInfo fallback.

## Kotlin pack (SDK-003)

The analog `kotlin/` pack applies to `android/sdk`. Consumer overlay:
`config/kotlin.profile.thresholds.yml` (95/95 line+branch, max CC 10).

CI jobs:

- `quality` (Ubuntu) and `android-sdk` (Ubuntu, Temurin 21,
  `PIXELDIVE_REQUIRE_JAVA=1`) run `scripts/check-android-sdk.sh`:
  `:sdk:ktlintCheck` (`KT-BUILD-002`), `:sdk:detekt` (`KT-CPLX-001/002`,
  `KT-BUILD-002`), and `:sdk:koverVerify` against the overlay (`KT-TEST-002`).
- `android-sdk` also runs Trivy filesystem scan of `android/` (`KT-SEC-004`;
  analog names OWASP Dependency-Check/grype — Trivy is proposed as an accepted
  evaluator in [kotlin.md](kotlin.md)).

Proposed Android-specific IDs (KT-AND-001/002, KT-SEC-005, KT-ENV-001) are in
[kotlin.md](kotlin.md), not in `docs/guardrail-deviations.yml`.

Gaps that remain:

- Android Lint (`KT-BUILD-002` when an Android module is present) does not
  apply to the JVM `:sdk` library. The Compose demo is not assembled in Linux CI.
- Kover excludes kotlinx.serialization `$$serializer` / `$Companion` generated
  classes, `@Serializable` wire DTOs (compiler-generated copy/equals default
  branches), and the JVM `DeviceSnapshot` / `JvmDeviceProbe` fallbacks (dead
  Elvis on `System.getProperty`). Production client/transport/Camera2Labels stay
  at 95/95.

