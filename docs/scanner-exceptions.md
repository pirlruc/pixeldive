# Scanner exceptions

Scope filters only. Finding-level ignores belong in `docs/guardrail-deviations.yml` plus a row here.

| Path / rule | Why this is not a product finding |
| --- | --- |
| `app/pb/` | Generated protobuf/gRPC stubs (`scripts/generate_proto.sh`). Fix the `.proto` or generator, not the stubs. |
| `docs/guardrails/` | Analog pin (private submodule). Not product code. |
| `.github/scaffold/` | Analog pin for issue templates. Not product code. |
