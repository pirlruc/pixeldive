# Guardrails 1.6.0 compliance (pixeldive)

Pin: [pirlruc/guardrails](https://github.com/pirlruc/guardrails) **1.6.0** at
`docs/guardrails/`, [pirlruc/github-scaffold](https://github.com/pirlruc/github-scaffold)
**1.5.0** at `.github/scaffold/`. Methodology citations follow scaffold 1.5.0
([methodologies 1.5.0](https://github.com/pirlruc/methodologies/tree/1.5.0/github-issue-adr)).

`docs/guardrail-deviations.yml` stays empty. Gaps that are not yet product
requirements (no published image, no uv migration) are open work in
[`docs/issues.yml`](../issues.yml), not silent deviations. Do not invent
`approved_by`.

## Python pack

| ID | Status |
|----|--------|
| PY-RUN-001 | Runtime is CPython 3.13. Install pin is `requirements.txt` (not `uv.lock`). See [README.md](README.md) PY-RUN-001 note. |
| PY-RUN-002 / PY-QUAL-001 | ruff format+lint, mypy in `scripts/ci-local.sh`. `lint_exception_max_days: 14` is in the consumer copy; noqa entries are not yet time-boxed. |
| PY-RUN-003 | 3.13 until 2027-04 ([QUAL-002](../issues.yml)). |
| PY-CPLX-001 | Consumer `max_cyclomatic_complexity: 8` (org 1.6.0). |
| PY-CPLX-002 | min MI 40; **avg MI 70** (stricter than org 60). Overlay reader allows stricter, forbids looser. |
| PY-TEST-002 | 95/95 statement/branch. |
| PY-DOC-001 | interrogate 95. |
| PY-DOC-002 | ruff pydocstyle Google. `pydoclint` is not in CI yet ([QUAL-003](../issues.yml)). |
| PY-SEC-002 | bandit in `ci-local.sh` and `security.yml`; CodeQL `security-extended` remains. |
| PY-SEC-003 | gitleaks 8.30.1 (aligned with pre-commit). |
| PY-SEC-004 | pip-audit in `ci-local.sh` and `security.yml` with `--no-deps --disable-pip` (pinned `requirements.txt`; no throwaway venv). |

## Docker / Compose

| ID | Status |
|----|--------|
| DOCKER-BUILD-001…005 | Multi-stage, slim, digest-pinned Python base, `.dockerignore`, no secrets in image. |
| DOCKER-RUN-001…006 | UID 65532, exec ENTRYPOINT, HEALTHCHECK, compose `read_only` + cap_drop + no-new-privileges. |
| DOCKER-COMPOSE-001 | Postgres image digest-pinned. MinIO still tag-pinned (Hub/scratch; [QUAL-003](../issues.yml)). |
| DOCKER-COMPOSE-002 | db + app have restart + healthcheck. MinIO server is scratch (no in-image probe). |
| DOCKER-COMPOSE-003 | Named volumes only. |
| DOCKER-COMPOSE-004 | Compose interpolates `${POSTGRES_PASSWORD}` / MinIO user; defaults remain for local demo. `.env` gitignored. |
| DOCKER-COMPOSE-005 | App drops ALL caps; no `privileged`. |
| DOCKER-COMPOSE-006 | Host ports bound to `127.0.0.1`. |
| DOCKER-COMPOSE-007 | `mem_limit` on db, app, minio. |
| DOCKER-COMPOSE-008 | Volume backup notes in README. |
| DOCKER-LINT-001/002, DOCKER-SEC-001, SC-SBOM/SIGN/PROV | Not run yet — no publish path. Tracked as [QUAL-003](../issues.yml). |

## CI / supply chain

| ID | Status |
|----|--------|
| CI-001…003, 005, 006, 008, 022, 025, 029 | SHA-pinned actions, concurrency, timeouts, High/Critical security fail, local parity, fail-closed thresholds, workflow `permissions:`, monthly security cron. |
| CI-012 | security.yml now includes gitleaks, CodeQL, bandit, pip-audit, dependency-review. |
| SC-DEP-001…003 | Multi-ecosystem Dependabot seed already present. |
| SC-DEP-004 | Gitlink SHA + annotated tags 1.6.0 / 1.5.0. |

## Security exclusions (not reduced further)

`app/pb/`, `docs/guardrails/`, and `.github/scaffold` remain CodeQL `paths-ignore`
scope filters ([scanner-exceptions.md](../scanner-exceptions.md)). They are not
product findings. No finding-level `nosec` / CodeQL suppressions were added.

In-code hardenings in this bump: HMAC API-key compare, in-process quota lock,
magic-byte upload sniff, production `ENVIRONMENT` fail-closed, download no longer
double-hits quotas, S3 “missing” no longer treats any `ClientError` whose message
contains `404` as not-found. Host-native HTTP/gRPC defaults are `127.0.0.1` so
bandit B104 is not suppressed; the image and Compose still set `0.0.0.0` inside
the container network.
