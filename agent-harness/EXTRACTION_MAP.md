# Extraction Map

This harness is extracted from Transmuter's working practices and generalized so
it can be reused across projects.

## What Was Extracted

| Transmuter practice | Reusable harness artifact |
| --- | --- |
| Vishwa-first issue triage | `core/sdlc-protocol.md`, `core/roles.yaml` |
| Named specialist agents | `core/roles.yaml` |
| Issue lifecycle labels | `core/sdlc-protocol.md`, `templates/ISSUE_TEMPLATES.md` |
| Prahari security review | `core/security-review.md` |
| Real API/browser acceptance standard | `core/testing-standard.md` |
| Router -> Service -> Repository | `core/architecture-patterns.md` |
| Money, multi-tenancy, AI guardrails | `core/quality-gates.md` |
| Frontend design skill | `skills/frontend-design-skill.md` |
| Package/API verification habit | `skills/package-verification-skill.md` |
| Persistent project context docs | `templates/PROJECT_CONTEXT.md` |
| Domain packs | `templates/DOMAIN_PACK.yaml` |
| Codex/Claude/Gemini instructions | `adapters/*` |

## What Was Deliberately Not Extracted

- Real secrets or credentials.
- Production tenant/customer data.
- Temporary passwords.
- Transmuter-specific hostnames as default harness values.
- Product-specific implementation details that would confuse other projects.

## How To Extend

Add new protocols only when they apply to multiple projects. Put product-specific
facts in the target project's `docs/team/PROJECT_CONTEXT.md`.

Good additions:

- A reusable mobile app testing gate.
- A reusable data migration checklist.
- A reusable SOC2 evidence checklist.
- A reusable prompt/eval template.

Poor additions:

- A single project's staging URL.
- A one-off customer workflow.
- Any secret or copied production config.

