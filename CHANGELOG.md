# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

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

### Added

- Dokka HTML for the Android SDK (`:sdk:dokkaGeneratePublicationHtml`).
  Public declarations without KDoc fail the task (KT-DOC-001).
- `ops-reuse.yml` calls commondevops `common-infra-lint` and containerdevops
  `container-iac` with the read tokens. This workflow does not check those
  repos out. Dependabot keeps the in-repo lint scripts.

### Changed

- Pin `docs/guardrails` to guardrails 1.8.0 and `.github/scaffold` to
  github-scaffold 1.7.0. Submodule names match commondevops.
- Sync scaffold 1.7.0 templates, Cursor rules, and agent instruction files.
- Cite methodologies 1.7.0 in consumer docs. Kotlin overlay carries the new
  `doc_coverage` and `lint_exception_max_days` keys.
- `COPY --chown` on image layers (DOCKER-BUILD-007). actionlint and zizmor run
  in local and CI workflow lint. CodeQL/Semgrep no longer exclude analog pins.
