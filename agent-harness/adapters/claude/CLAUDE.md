# Claude Code Adapter

This project uses the reusable Agent Harness. Claude Code should follow the
model-neutral core protocols and use this adapter for Claude-specific behavior.

## Load Order

1. `agent-harness/core/operating-principles.md`
2. `agent-harness/core/sdlc-protocol.md`
3. `agent-harness/core/roles.yaml`
4. `docs/team/PROJECT_CONTEXT.md`
5. Relevant architecture, design, security, and testing docs.

## Work Protocol

- Default role is Vishwa.
- Open or reuse an issue before tracked edits.
- Keep implementation narrow and evidence-backed.
- Ask a clarifying question only when a safe assumption is not possible.
- Use Prahari review triggers exactly as defined in the core security review.

## Claude Code Notes

- Prefer concise plans, then execute.
- Use existing project commands rather than inventing toolchains.
- Keep final responses focused on changed files, verification, and risk.
- Do not expose secrets in logs or responses.

