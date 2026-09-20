# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`,
which has no entries).

| Limit | Why |
| --- | --- |
| Analog submodules not cloned | `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set ([TOOL-001-T1](issues.yml)). |
| GitHub issues not published | Issue create is a publishing action. Tracked as [TOOL-002](issues.yml). |
| Tests use SQLite locally | Production is PostgreSQL + asyncpg. SQLite stays the unit-test default; CI job `postgres` is [DATA-003](issues.yml). |
| Auth is opt-in | `AUTH_REQUIRED` defaults to false so local tests and compose stay unauthenticated. Set it (and `API_KEYS`) for production; gRPC TLS is also explicit via `GRPC_INSECURE`. |
| Quotas are per-process | [SEC-002](issues.yml) is an in-memory limiter. Multi-replica shared accounting is [SEC-004](issues.yml). |
| GC age window defaults to 0 | `GC_MIN_AGE_SECONDS=0` skips the delete-time grace used to protect concurrent same-hash uploads. Set a positive value and `ORPHAN_SWEEP_INTERVAL_SECONDS` in production ([DATA-004](issues.yml)). |
| Host may lack `python3-venv` | Use `pip install --target .venv` or `pip install --prefix .venv` (Debian: `.venv/local/...`). `scripts/python-env.sh` resolves both layouts. Do not install into the system OS. |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.12.14-slim-bookworm`. Dependabot Docker majors (3.14) stay a runtime decision ([QUAL-002](issues.yml)). Multi-arch deploys need a manifest-list digest. |
| PR size soft limit | PY-DELIV-001 is a 500-line soft limit. Phase 3 hardening is intentionally larger than that. |
