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
| KICS `698ed579-…` on `minio-init` (`kics-scan ignore-block`) | See below. One-shot bucket bootstrap, not a daemon. |
| KICS `ce76b7d0-…` on `db.cap_add` (`kics-scan ignore-line`) | See below. Postgres entrypoint caps after `cap_drop: ALL`. |

## Why these KICS exclusions exist in pixeldive

Both ignores are on `docker-compose.yml` because the queries describe shapes
this service needs, and the docker pack already allows those shapes.

### `minio-init` and query `698ed579` (healthcheck)

The S3 profile is optional. Default `docker compose up` stays on the local
disk. When the `s3` profile is on, `minio` is the long-running server
(`quay.io/minio/minio`, healthcheck `mc ready local`). `minio-init` is a
second container, `quay.io/minio/mc`, whose only job is to wait until that
server answers, run `mc mb --ignore-existing local/pixeldive`, and exit.
`app` waits with `condition: service_completed_successfully` and
`required: false`, so a stack without the profile does not block on it.

Query `698ed579` flags every Compose service that has no `healthcheck:`.
A healthcheck would tell Compose to treat the finished `mc` process as a
daemon that must stay healthy ([DOCKER-COMPOSE-002](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md)
is the opposite: one-shot jobs are not long-running services). The ignore
is the block above `minio-init` only. `db`, `app`, and `minio` keep
healthchecks.

### `db.cap_add` and query `ce76b7d0`

`db` is `postgres:16-alpine`. The official entrypoint must create or chown
`/var/lib/postgresql/data` and then `gosu` down to the `postgres` user.
That needs `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETGID`, and `SETUID`.
[DOCKER-COMPOSE-005](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md)
also requires `cap_drop: ALL`, so the file drops every capability and adds
those five back. Query `ce76b7d0` flags any `cap_add`, including that
narrow list. Removing the adds stops Postgres from starting. Removing
`cap_drop: ALL` would miss the guardrail. `app` and `minio` drop `ALL`
and add nothing; the ignore is the single line above `db.cap_add`.
| Trivy `ignore-unfixed` on `pixeldive:ci`, `ios/`, and `android/` | Debian bookworm CVEs in `python:3.13.15-slim-bookworm` with `will_not_fix` / `fix_deferred` (zlib, perl, sqlite, util-linux, ncurses), and the same class of unfixed OS findings in mobile trees. No in-repo patch exists; Dependabot digest bumps pick up fixes ([DOCKER-BUILD-006](https://github.com/pirlruc/guardrails/blob/1.8.0/docker/guardrails.md), SWIFT-SEC-004, KT-SEC-004). Fixable findings still fail the job. |
