# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`,
which has no entries).

| Limit | Why |
| --- | --- |
| Analog submodules not cloned | `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set ([TOOL-001-T1](issues.yml)). |
| GitHub issues not published | Issue create is a publishing action. Tracked as [TOOL-002](issues.yml). |
| Tests use SQLite | Production is PostgreSQL + asyncpg. SQLite stays the unit-test default; Postgres CI is [DATA-003](issues.yml). |
| Auth is opt-in | `AUTH_REQUIRED` defaults to false so local tests and compose stay unauthenticated. Set it (and `API_KEYS`) for production; gRPC TLS is also explicit via `GRPC_INSECURE`. |
| GC age window defaults to 0 | `GC_MIN_AGE_SECONDS=0` skips the delete-time grace used to protect concurrent same-hash uploads. Set a positive value in production ([DATA-004](issues.yml)). |
| S3 save_file still buffers the spool | [PERF-002](issues.yml) awaits aiobotocore. Whole-object PUT memory is [PERF-003](issues.yml). |
| Host may lack `python3-venv` | Use `pip install --target .venv` and `PYTHONPATH=.venv` rather than a system OS install. |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.12.14-slim-bookworm`. Multi-arch deploys need a manifest-list digest. |
| PR size soft limit | PY-DELIV-001 is a 500-line soft limit. Phase 2 + SDK + demo is intentionally larger than that. |
