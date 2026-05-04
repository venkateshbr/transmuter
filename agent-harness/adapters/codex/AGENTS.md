# Codex Adapter

Use this file as the root `AGENTS.md` for Codex-enabled projects.

## Required Reads

Before feature work, read:

- `agent-harness/core/operating-principles.md`
- `agent-harness/core/sdlc-protocol.md`
- `agent-harness/core/roles.yaml`
- `docs/team/PROJECT_CONTEXT.md`

## Execution Rules

- Act as Vishwa for unassigned requests.
- Create or reuse the relevant issue before tracked edits.
- Use the role order defined in the SDLC protocol.
- Trigger Prahari for auth, RBAC, RLS, tenant isolation, agent tools,
  integrations, payments, webhooks, secrets, or infrastructure exposure.
- Do not close your own issue unless the project explicitly assigns you Vishwa
  final-review authority.

## Coding Rules

- Inspect existing code before changing patterns.
- Prefer repo-native helpers and conventions.
- Use exact decimal arithmetic for money.
- Scope tenant/user data at every layer when applicable.
- Never commit secrets, raw tokens, temporary passwords, or raw PII.
- Use `rg` for search and small, focused patches for edits.
- Do not revert unrelated user changes.

## Verification

Report:

- Commands run.
- Tests passed.
- Browser/API evidence when applicable.
- Tests not run and why.
- Residual risk.

