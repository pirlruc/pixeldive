---
name: ansible-roles
description: 'Ansible role and playbook changes. Use when editing files that match: roles/**,**/playbooks/**.'
paths: roles/**,**/playbooks/**
disable-model-invocation: true
---

<!-- Generated from .cursor/rules by scripts/render-agent-instructions.py. Edit the .mdc files, then re-run that script. -->

Cursor applies the matching `.cursor/rules` file by glob and does not auto-invoke this skill. Other agents should follow this skill when the description matches.

# Ansible roles

Org principles live in `docs/guardrails/ansible/` (`ANSIBLE-*`).

1. `supported_platforms` is an allowed set. Test every platform this repo declares, not every platform the org lists (ANSIBLE-RUN-001, ANSIBLE-TEST-001).
2. Secrets are hashes, Vault, SOPS with Age, or runtime lookups. Not plaintext (ANSIBLE-SEC-001).
3. A secret task argument sets `no_log` (ANSIBLE-SEC-002).
4. YAML for playbooks and roles passes yamllint (ANSIBLE-LINT-002). There is no separate YAML pack.
