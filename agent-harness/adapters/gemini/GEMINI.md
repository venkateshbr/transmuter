# Gemini Adapter

This project uses the reusable Agent Harness. Gemini should follow the core
protocols and use this adapter for Gemini-specific project behavior.

## Required Context

- `agent-harness/core/operating-principles.md`
- `agent-harness/core/sdlc-protocol.md`
- `agent-harness/core/quality-gates.md`
- `docs/team/PROJECT_CONTEXT.md`

## Rules

- Vishwa is the default role.
- Create/reuse an issue before changing tracked files.
- Follow the role pipeline and lifecycle labels.
- Use existing architecture and design patterns.
- Verify current package/API behavior before integration code.
- Never log or return JWTs, API keys, secrets, or raw PII.

## Completion Format

Include:

- Summary.
- Files changed.
- Verification.
- Security/review gates.
- Residual risk.

