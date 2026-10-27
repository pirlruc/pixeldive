# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- setuptools in the lock is 84.2.1. Dependabot's updater reported
  "No files have changed" for 84.0.0 to 84.1.0, and it cannot clone
  the github-scaffold submodule.
- The security workflow rescans the published 0.1.0 linux/amd64 image
  through containerdevops 6.3.5. Image workflow pins move to the same
  commit. The runtime image is unchanged, so there is no 0.1.1.

## [0.1.0] - 2026-10-23

### Fixed

- Publish smoke command is `python -m app.settings_storage`.
  `verify-multiarch.sh` word-splits `verify_command` and keeps quote
  characters, so `python -c "import app"` never reached cosign.
- Bump aiohttp to 3.14.5, multidict to 6.9.1, Mako to 1.4.3, and
  certifi to 2026.10.23 so pip-audit is clean. Move the image base to
  `python:3.13.17-slim-trixie`, which has no fixable HIGH or CRITICAL
  OS findings. Group Dependabot uv security updates into one pull request.
- Create `/data/images` as root before `USER 65532`. The previous order
  made the image build fail with permission denied.
- Find Swift 6.4 Linux test bundles (`PixeldiveSDKTests.xctest` directories).
- Dependabot fallbacks use `github.event.pull_request.user.login`.
  `github.actor` is the spoofable check zizmor rejects.
- `.shellcheckrc` sets `source-path=SCRIPTDIR` so ShellCheck follows
  `source=python-env.sh`. ShellCheck 0.11 ignores a `severity=` key, and
  `common-infra-lint` passes no `--severity`. `RUFF` assignments disable
  SC2034 because callers read the array and arrays cannot be exported.
  Local `scripts/run-shellcheck.sh` still uses `--severity=error`.
- Refuse an auth-disabled bind that is not loopback unless `PIXELDIVE_ALLOW_ANONYMOUS=true`.
- Remove the default database password. `AUTO_CREATE_TABLES` defaults to false. `gc_min_age_seconds` defaults to 60. Duplicate API tokens are rejected at startup.
- Pin swift-nio 2.104.0. Release 2.97.1 has fixed HIGH findings, and
  2.98.0 needs Swift tools 6.1, so the Linux package test image is `swift:6.1`.
- Shell scripts match shfmt 3.11 with `[*.sh]` indent 2. Dependabot
  waits 7 days before proposing a newly published version. The launcher
  activity stays exported, and the loopback healthcheck keeps
  `HTTPSConnection` with a verifying SSL context.

### Added

- PostgreSQL `tenant_quota` for shared rate and byte caps (SEC-004), and an optional Redis backend behind the Compose `redis` profile (SEC-005). The default without those URLs stays in-process.
- Mobile TLS gRPC constructors beside `insecure()`, protobuf Struct metadata (field 8), and an optional PEM CA on iOS and Android (SDK-007, SDK-008).
- `docs/docker-hub.md` and `docs/github-packages.md` for the 0.1.0 image. `/metrics` is unauthenticated Prometheus text on the HTTP port.
- `scripts/check-ci-local.sh` and `scripts/check-ci-docker.sh`. `ops-reuse.yml` calls commondevops `0932c7bf` and containerdevops 6.3.3. That pin puts tools installed on the public image onto `PATH` and allows `pip install --user` on Ubuntu 24.04. Infra, secrets, and supply-chain use a public GHCR Ubuntu image with `mount_runner_git: false`, because this repo cannot pull the private ci images and the host library mounts replace libraries that image's bash needs. `python-quality` is not called: its consumer file is the org profile, and this repo's average maintainability floor is 70.
- Dokka HTML for the Android SDK (`:sdk:dokkaGeneratePublicationHtml`).
  Public declarations without KDoc fail the task (KT-DOC-001).
- `ops-reuse.yml` calls commondevops `common-infra-lint` and containerdevops
  `container-iac` with the read tokens. This workflow does not check those
  repos out. Dependabot keeps the in-repo lint scripts.

### Changed

- Pin `docs/guardrails` to guardrails 1.13.1 and `.github/scaffold` to github-scaffold 1.10.2.
- Alembic `0001_phase2` is an explicit schema. `0002_tenant_quota` adds the shared quota table. `alembic check` runs in the Postgres job.
- Proto stubs are checked with `git diff --exit-code -- app/pb` after `generate_proto.sh`.
- Sync scaffold 1.7.0 templates, Cursor rules, and agent instruction files.
- Cite methodologies 1.7.0 in consumer docs. Kotlin overlay carries the new
  `doc_coverage` and `lint_exception_max_days` keys.
- `COPY --chown` on image layers (DOCKER-BUILD-007). actionlint and zizmor run
  in local and CI workflow lint. CodeQL/Semgrep no longer exclude analog pins.
