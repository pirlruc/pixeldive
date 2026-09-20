# Proposed guardrails (pixeldive → org)

Proposals for [pirlruc/guardrails](https://github.com/pirlruc/guardrails) after reviewing
this service against pin **1.6.0**. These are **not** in-repo deviations and are **not**
github-issue-adr decision records. Implement them in the analog repo (new IDs or edits
to existing IDs), then bump the `docs/guardrails` gitlink here.

Companion: [compliance-1.6.0.md](compliance-1.6.0.md) (what this repo already does vs 1.6.0).
Swift/iOS proposals (Kotlin analog): [swift.md](swift.md).

## New IDs to add

### PY-SEC-005 — Constant-time credential compare

API tokens, passwords, and similar secrets must not use short-circuiting `==` /
`dict` membership on the secret value. Require `hmac.compare_digest` (or equivalent)
against the configured set. Distinct from [PY-SEC-003](https://github.com/pirlruc/guardrails/blob/1.6.0/python/guardrails.md) (secret scanning).

**Why here:** `authenticate()` previously used `token not in keys`. That is a
timing side channel on bearer tokens.

### PY-SEC-006 — Production profile fail-closed

A named production environment (`ENVIRONMENT=production` or equivalent) must refuse
to start when authentication is off or when a plaintext gRPC/HTTP listener is the
only bind. Local/dev defaults may stay open; production must not. Distinct from
language SAST ([PY-SEC-002](https://github.com/pirlruc/guardrails/blob/1.6.0/python/guardrails.md)).

**Why here:** `AUTH_REQUIRED=false` and `GRPC_INSECURE=true` are correct for tests
and Compose, and are a production footgun without a fail-closed profile.

### PY-SEC-007 — Sniff declared Content-Type for untrusted uploads

When a service accepts caller-declared binary types (images, archives), first-byte
magic must match the declared type. Content-Type alone is not a security control.
Optional threshold: minimum header bytes (16).

**Why here:** any bytes with `Content-Type: image/png` were stored as PNG.

### PY-API-003 — Dual-transport error map

Services that expose the same domain API on more than one transport (REST + gRPC,
HTTP + GraphQL, …) must maintain **one** exception → status table. Drift between
HTTP 404 and gRPC `NOT_FOUND` (and similar pairs) is a defect.

**Why here:** `http_errors.py` and `grpc_errors.py` duplicated the same registry.

### PY-ASYNC-001 — Abort/cancel helpers are `NoReturn`

gRPC `context.abort`, asyncio cancellation helpers, and similar “does not return”
APIs must be typed `NoReturn` and must not be followed by reachable success-path
code. Distinct from [PY-PERF-002](https://github.com/pirlruc/guardrails/blob/1.6.0/python/guardrails.md) (event-loop assumptions).

**Why here:** several stream assemblers continued after `await context.abort(...)`.

### DOCKER-COMPOSE-009 — Scratch images and healthchecks

[DOCKER-COMPOSE-002](https://github.com/pirlruc/guardrails/blob/1.6.0/docker/guardrails.md)
requires a `healthcheck:` on every long-running service. Scratch/distroless third-party
images (MinIO server) often have no `curl`/`sh` to probe with. The org rule should
allow an explicit exception: dependents retry/wait, and the gap is listed in the
consumer’s scanner/limitations doc — not a silent omit.

**Why here:** Hub `minio/minio` is scratch-based; an HTTP healthcheck inside that
container cannot run. pixeldive now uses the quay image that ships `mc ready local`.
The org rule still needs an explicit scratch/distroless exception for images that
do not.

### PY-CPLX-003 — File-split vs duplication

[PY-CPLX-001](https://github.com/pirlruc/guardrails/blob/1.6.0/python/guardrails.md) /
[PY-CPLX-002](https://github.com/pirlruc/guardrails/blob/1.6.0/python/guardrails.md)
are per-file. Splitting a module to keep max CC ≤ 8 and min MI ≥ 40 routinely
duplicates try/except, status maps, and mixin stubs. Add a principle: extracting a
shared helper is preferred to copying the same 8-line wrapper into a new file.
Numeric gate stays per-file; this is a design rule, not a second radon number.

## Changes to existing IDs

### PY-RUN-001 — Lockfile family, not uv-only

The 1.6.0 profile names `uv` + `uv.lock`. pixeldive now commits `uv.lock` and
keeps `requirements.txt` as `uv export` for Docker/pip-audit. Treat uv, poetry,
pip-tools, and a committed `requirements.txt` of pinned versions as equivalent
lockfiles at the org level so other pip consumers are not forced onto uv.

### PY-SEC-004 — Audit the lockfile without a throwaway venv

`pip-audit -r requirements.txt` creates a temporary venv. Hosts without
`ensurepip` (Debian `python3-venv` missing) cannot run that. When the file is
already a fully pinned lock (every line `==`), `--no-deps --disable-pip` audits
the pin list directly. Document that as an accepted evaluator for pip-tools /
committed `requirements.txt` consumers; keep the temp-venv path for uv/poetry
projects that still need resolution.

### PY-SEC-002 — CodeQL `security-extended` as accepted SAST; no bind-all nosec

The profile lists `semgrep` and `bandit`. GitHub-hosted Python repos already run
CodeQL `security-extended` and fail on High/Critical ([CI-005](https://github.com/pirlruc/guardrails/blob/1.6.0/ci/guardrails.md)).
Document CodeQL as an accepted SAST evaluator *in addition to* bandit, so
consumers are not required to run three overlapping SAST tools. Bandit remains
useful for Python-idiom checks CodeQL misses (`assert`, `exec`, bind-all).

Bandit B104 flags `0.0.0.0` literals in settings. Host-native defaults should
be loopback. Images and Compose set `HTTP_HOST`/`GRPC_HOST=0.0.0.0` inside the
container network. Do not `# nosec B104` a process-wide default.

### PY-CPLX-001 max CC 10 → 8 (already shipped in 1.6.0)

Keep 8. Call out in `python/profile.md` that consumers who split files to meet
the gate must not duplicate transport wrappers (see PY-CPLX-003 above).

### SC-DEP-004 + private analog clones

The gitlink freshness assert is right. Consumers that cannot clone private
`docs/guardrails` on every developer laptop already keep a consumer copy
(`config/python.profile.thresholds.yml`) and overlay-compare when the analog is
present. Document that pattern in the SC-DEP-004 recipe so it is not reinvented.

### DOCKER-COMPOSE-001 vs Hub rate limits

Pinning third-party images by digest is right. Dependabot’s `docker` ecosystem
does not refresh tags inside Compose files. Either extend the Dependabot seed
comments or accept a documented “tag + scheduled digest bump” path for Compose
third-party images.

## Do not add

- A guardrail that forbids unauthenticated `/metrics` on an internal scrape
  network. Prometheus scrape of counters is normal; document network exposure
  instead (already implied by bind-address / Compose port-bind rules).
- An org requirement to fail CI on CodeQL **medium**. [CI-005](https://github.com/pirlruc/guardrails/blob/1.6.0/ci/guardrails.md)
  is High/Critical. Stricter is allowed per-repo without a new ID.

## Swift / iOS

The analog already ships a `swift/` pack. After adding `ios/PixeldiveSDK`, several
Kotlin/Android rules still have no Swift twin (complexity, structured concurrency,
ATS, token storage). Those proposals, plus a SWIFT-ENV-001 overlay for
Foundation-only `swift test` on Linux, live in [swift.md](swift.md).

## Kotlin / Android

The analog already ships a `kotlin/` pack. After adding `android/` (JVM OkHttp SDK +
Compose demo), Android-specific twins of SWIFT-IOS-003/004 and SWIFT-SEC-005 were
still missing, as was a Linux JVM test overlay. Those proposals live in
[kotlin.md](kotlin.md).
