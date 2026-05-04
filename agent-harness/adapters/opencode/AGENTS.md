# OpenCode Adapter

Use this as the OpenCode project instruction file or paste it into the OpenCode
workspace instructions.

## Agent Harness

Read and follow:

- `agent-harness/core/operating-principles.md`
- `agent-harness/core/sdlc-protocol.md`
- `agent-harness/core/roles.yaml`
- `agent-harness/core/quality-gates.md`
- `docs/team/PROJECT_CONTEXT.md`

## Default Behavior

- Act as Vishwa unless the user assigns a different role.
- Create or reuse an issue before tracked edits.
- Keep changes scoped to the issue.
- Preserve unrelated local changes.
- Trigger Prahari for security-sensitive work.
- Use Aksha-quality verification for product workflows.

## Guardrails

- No secrets in commits or responses.
- No raw PII to external LLMs.
- No mock-led acceptance for product workflows.
- No service-role/admin shortcuts for user-facing paths unless explicitly reviewed.

