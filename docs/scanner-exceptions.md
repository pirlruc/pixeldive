# Scanner exceptions

Scope filters only. Finding-level ignores belong in `docs/guardrail-deviations.yml` plus a row here.

| Path / rule | Why this is not a product finding |
| --- | --- |
| `app/pb/` | Generated protobuf/gRPC stubs (`scripts/generate_proto.sh`). Fix the `.proto` or generator, not the stubs. |
| `docs/guardrails/` | Analog pin (private submodule). Not product code. |
| `.github/scaffold/` | Analog pin for issue templates. Not product code. |
| KICS `698ed579-…` on `minio-init` (`kics-scan ignore-block`) | One-shot `mc` bootstrap, not a long-running service. Dependents use `condition: service_completed_successfully` ([DOCKER-COMPOSE-002](https://github.com/pirlruc/guardrails/blob/1.6.0/docker/guardrails.md)). |
| KICS `ce76b7d0-…` on `db.cap_add` (`kics-scan ignore-line`) | Postgres entrypoint must chown the data dir then `gosu` after `cap_drop: ALL` ([DOCKER-COMPOSE-005](https://github.com/pirlruc/guardrails/blob/1.6.0/docker/guardrails.md)). The query flags any `cap_add`. |
