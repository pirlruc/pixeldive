# Limitations

Untracked limits (not silent guardrail deviations — see `docs/guardrail-deviations.yml`).

| Limit | Why |
| --- | --- |
| Analog submodules not cloned | `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI falls back to `config/python.profile.thresholds.yml` until `GUARDRAILS_READ_TOKEN` is set. |
| GitHub issues not published | Issue create is a publishing action. `docs/issues.yml` is the decision log until Issues write is granted and `issues-sync.py` runs. |
| Tests use SQLite | Production is PostgreSQL + asyncpg. Tests use `sqlite+aiosqlite` so CI does not need a running Postgres. |
| No authentication | Phase 1 is a session ingest API on a trusted network. Auth is follow-up work. |
| `init_db()` is create_all | Empty databases get tables automatically. Evolving a live schema needs Alembic (not in Phase 1). |
| Image Dockerfile digest | Base image is pinned to the published linux/amd64 digest of `python:3.12.14-slim-bookworm`. Multi-arch deploys need a manifest-list digest. |
