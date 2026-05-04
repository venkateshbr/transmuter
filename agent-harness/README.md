# Agent Harness

A reusable AI operating system for software projects. It packages the strongest
practices extracted from Transmuter into a portable harness that can be copied
into any repository and used with Codex, Claude Code, Gemini, OpenCode, or other
coding agents.

The harness is intentionally model-neutral. The core protocols define how work
should happen; the adapters translate those protocols into the files each agent
tool naturally reads.

## What It Provides

- Issue-first SDLC with explicit lifecycle states.
- Named specialist roles for requirements, architecture, design, implementation,
  security, testing, deployment, and final review.
- Security and integration review gates.
- Real acceptance testing standards, not smoke-test theater.
- Architecture and code quality patterns.
- Reusable skill templates.
- Model-specific adapter prompts for Codex, Claude Code, Gemini, and OpenCode.
- Project bootstrap checklist for applying the harness to a new repo.

## Directory Layout

```text
agent-harness/
  README.md
  core/
    operating-principles.md
    sdlc-protocol.md
    roles.yaml
    quality-gates.md
    architecture-patterns.md
    security-review.md
    testing-standard.md
  skills/
    SKILL_TEMPLATE.md
    frontend-design-skill.md
    package-verification-skill.md
  adapters/
    codex/AGENTS.md
    claude/CLAUDE.md
    gemini/GEMINI.md
    opencode/AGENTS.md
  templates/
    PROJECT_CONTEXT.md
    DOMAIN_PACK.yaml
    ISSUE_TEMPLATES.md
    PR_TEMPLATE.md
    ENVIRONMENT_CONFIGURATION.md
```

## Quick Start In Another Project

1. Copy the harness into the target repo:

   ```bash
   cp -R agent-harness /path/to/target-repo/agent-harness
   ```

2. Pick the adapter files for the tools you use:

   ```bash
   cp agent-harness/adapters/codex/AGENTS.md /path/to/target-repo/AGENTS.md
   cp agent-harness/adapters/claude/CLAUDE.md /path/to/target-repo/CLAUDE.md
   cp agent-harness/adapters/gemini/GEMINI.md /path/to/target-repo/GEMINI.md
   ```

   For OpenCode, either copy `agent-harness/adapters/opencode/AGENTS.md` to the
   location OpenCode reads in your setup, or paste it into your OpenCode project
   instructions.

3. Create project-specific context:

   ```bash
   mkdir -p docs/team domain_packs/<your-domain> .github
   cp agent-harness/templates/PROJECT_CONTEXT.md docs/team/PROJECT_CONTEXT.md
   cp agent-harness/templates/DOMAIN_PACK.yaml domain_packs/<your-domain>/pack.yaml
   cp agent-harness/templates/PR_TEMPLATE.md .github/pull_request_template.md
   ```

4. Customize the placeholders:

   - Repository URL and issue tracker.
   - Stack and package manager commands.
   - Domain pack name.
   - Security-sensitive areas.
   - Real acceptance test commands.
   - Design system and frontend conventions.
   - Deployment and environment docs.

5. Ask every agent to read:

   - `AGENTS.md` or its model-specific equivalent.
   - `agent-harness/core/sdlc-protocol.md`.
   - `docs/team/PROJECT_CONTEXT.md`.
   - Any domain-specific architecture/design/test docs.

## Recommended Adoption Order

1. Start with `core/operating-principles.md` and `core/sdlc-protocol.md`.
2. Add `roles.yaml` so agents know which hat they are wearing.
3. Add `quality-gates.md`, `security-review.md`, and `testing-standard.md`.
4. Add architecture and design skills once the repo has enough patterns.
5. Add model adapters only after the core docs are stable.

## Project Customization Rules

- Keep the core protocol generic.
- Put project facts in `docs/team/PROJECT_CONTEXT.md`.
- Put domain entities and workflow gates in `domain_packs/<domain>/pack.yaml`.
- Put model-specific quirks in `adapters/<tool>/`.
- Never store secrets in the harness.
- Prefer examples with placeholders over real production values.

## How To Use During Work

Every request should start the same way:

1. Vishwa triages the request.
2. Create or reuse an issue.
3. Identify required roles and gates.
4. Load the narrowest relevant context.
5. Implement with repo-native patterns.
6. Verify with real acceptance evidence.
7. Document residual risk and close through the issue lifecycle.

## Naming

You can call this an **Agent Harness**, **AI Operating System**, or **Agentic SDLC
Harness**. In code and docs, `agent-harness` is short, portable, and tool-neutral.

