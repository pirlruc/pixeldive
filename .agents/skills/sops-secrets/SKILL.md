---
name: sops-secrets
description: 'SOPS and Age secret files. Use when editing files that match: **/*.sops.*,**/.sops.yaml.'
paths: '**/*.sops.*,**/.sops.yaml'
disable-model-invocation: true
---

<!-- Generated from .cursor/rules by scripts/render-agent-instructions.py. Edit the .mdc files, then re-run that script. -->

Cursor applies the matching `.cursor/rules` file by glob and does not auto-invoke this skill. Other agents should follow this skill when the description matches.

# SOPS secrets

Org principles live in `docs/guardrails/secrets/` (`SOPS-*`).

1. Committed secret files are ciphertext (SOPS-SEC-001).
2. Age recipients are real keys, named in `.sops.yaml` (SOPS-SEC-002).
3. The private key is not in the repository and not in CI (SOPS-SEC-003).
4. CI checks encryption and does not decrypt (SOPS-LINT-001).
