# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`,
which has no entries).

| Limit | Why |
| --- | --- |
| Analog submodules not cloned | `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set ([TOOL-001-T1](issues.yml)). |
| GitHub issues not published | Issue create is a publishing action. `docs/issues.yml` is the decision log until Issues write is granted and `issues-sync.py` runs. |
| Tests use SQLite | Production is PostgreSQL + asyncpg. Tests use `sqlite+aiosqlite` so CI does not need a running Postgres. |
| Auth is opt-in | `AUTH_REQUIRED` defaults to false so local tests and compose stay unauthenticated. Set it (and `API_KEYS`) for production; gRPC TLS is also explicit via `GRPC_INSECURE`. |
| S3 uses boto3 on worker threads | PERF-001 removed HEAD-before-PUT and spools uploads. An async S3 client is [PERF-002](issues.yml). |
| Host may lack `python3-venv` | Use `pip install --target .venv` and `PYTHONPATH=.venv` rather than a system OS install. |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.12.14-slim-bookworm`. Multi-arch deploys need a manifest-list digest. |
| PR size soft limit | PY-DELIV-001 is a 500-line soft limit. Phase 2 + SDK + demo is intentionally larger than that. |
