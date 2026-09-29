# Scanner exceptions

Scope filters only. Finding-level ignores belong in `docs/guardrail-deviations.yml` plus a row here.

Analog checkouts (`docs/guardrails/`, `.github/scaffold/`) are no longer listed. CodeQL and
Semgrep do not scan them: security CI does not init those submodules, and the Semgrep
targets are product trees (`app`, `sdk`, `demo`, `scripts`, `ios`, `android`).

| Path / rule | Why this is not a product finding |
| --- | --- |
| `app/pb/` | Generated protobuf/gRPC stubs (`scripts/generate_proto.sh`). Fix the `.proto` or generator, not the stubs. CodeQL `paths-ignore`, Semgrep `--exclude`, and bandit `-x` all use this scope. |
| `ios/.build`, `ios/Demo/PixeldiveDemo.xcodeproj` | SPM checkout and Xcode project. `ios-sdk` Trivy also sets `skip-dirs: .build` because grpc-swift / swift-nio-ssl samples ship private keys (SWIFT-SEC-004). |
| `android/.gradle`, `android/**/build` | Gradle caches and build output. Not product source. |
| KICS `698ed579-…` on `minio-init` (`kics-scan ignore-block`) | One-shot `mc` bootstrap, not a long-running service. Dependents use `condition: service_completed_successfully` ([DOCKER-COMPOSE-002](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md)). The query still flags any service without a healthcheck. |
| KICS `ce76b7d0-…` on `db.cap_add` (`kics-scan ignore-line`) | Postgres entrypoint must chown the data dir then `gosu` after `cap_drop: ALL` ([DOCKER-COMPOSE-005](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md)). The query flags any `cap_add`. Dropping the caps breaks the official entrypoint; dropping `cap_drop: ALL` would miss DOCKER-COMPOSE-005. |
| Trivy `ignore-unfixed` on `pixeldive:ci`, `ios/`, and `android/` | Debian bookworm CVEs in `python:3.13.15-slim-bookworm` with `will_not_fix` / `fix_deferred` (zlib, perl, sqlite, util-linux, ncurses), and the same class of unfixed OS findings in mobile trees. No in-repo patch exists; Dependabot digest bumps pick up fixes ([DOCKER-BUILD-006](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md), SWIFT-SEC-004, KT-SEC-004). Fixable findings still fail the job. |
