---
name: opentofu-iac
description: 'OpenTofu and HCL changes. Use when editing files that match: **/*.tf,**/*.tfvars,**/*.hcl.'
paths: '**/*.tf,**/*.tfvars,**/*.hcl'
disable-model-invocation: true
---

<!-- Generated from .cursor/rules by scripts/render-agent-instructions.py. Edit the .mdc files, then re-run that script. -->

Cursor applies the matching `.cursor/rules` file by glob and does not auto-invoke this skill. Other agents should follow this skill when the description matches.

# OpenTofu

Org principles live in `docs/guardrails/opentofu/` (`TOFU-*`). HCL is not
DOCKER-LINT-002.

1. `tofu fmt` and `tofu validate` pass (TOFU-LINT-001, TOFU-LINT-002).
2. tflint uses the committed config (TOFU-LINT-003).
3. Commit `.terraform.lock.hcl` (TOFU-BUILD-001).
4. State is encrypted. No secret literals in HCL (TOFU-SEC-001, TOFU-SEC-002).
5. Stateful resources set `prevent_destroy` (TOFU-SEC-003).
6. A pull request carries a plan. CI does not apply (TOFU-TEST-001).
