# Transmuter SDLC Protocol — Mandatory Engineering Process

**Owner**: Vishwa  
**Status**: Canonical living document  
**Last Updated**: 2026-05-02

GitHub Issues at https://github.com/venkateshbr/transmuter are the single source of truth for all work. Nothing gets built without a ticket.

---

## 1. Mandatory First Step

Every agent, every time, before changing code or tracked project files:

1. Identify the role. If no role is specified, act as **Vishwa**.
2. Sync GitHub Issues:
   ```bash
   /Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue list --state open --limit 20 --repo venkateshbr/transmuter
   ```
3. Find or create the relevant issue.
4. Confirm the issue has the correct `agent:*`, `type:*`, `priority:*`, and `status:*` labels.
5. Move the active issue to `status:in-progress` before implementation:
   ```bash
   /Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue edit <id> --remove-label "status:assigned" --add-label "status:in-progress" --repo venkateshbr/transmuter
   ```
6. Do the work.
7. When implementation is complete, move the issue to `status:in-qa` and open a PR with `Fixes #<issue_id>`.

No code may be written before a relevant GitHub issue exists and is in progress.

---

## 2. Vishwa-First Protocol

All founder requests route through **Vishwa** first.

Vishwa must:

1. Analyze scope, urgency, impact, dependencies, and security triggers.
2. Create or reuse a parent issue.
3. Decompose work into sub-issues assigned to the correct specialists.
4. Ensure feature work follows the execution order in section 3.
5. Review all output and PRs before presenting completion to the founder.

Vishwa seeks founder approval before non-trivial action. Agents do not self-start.

---

## 3. Agent Execution Order

Full feature pipeline:

```text
Netra (requirements + user stories)
  -> Vastu (architecture + API/schema design)
  -> Chitra (UI/UX design spec, if frontend involved)
  -> Karya + Rupa (backend + frontend implementation)
  -> Vastu (post-implementation architecture review)
  -> Aksha (real API + browser UI testing)
  -> Sthira (CI/CD, infra, deployment readiness)
  -> Vishwa (final review, PR merge, issue close)
```

Shortcuts:

- Bug fix: Vishwa may assign directly to Karya or Rupa.
- UI-only change: Chitra -> Rupa -> Aksha.
- Backend-only change: Karya -> Aksha.
- Infrastructure/CI change: Sthira -> Aksha.

Prahari is mandatory before `status:in-review` for auth, JWT, RLS, RBAC, agent tools, external integrations, or security-sensitive changes.

---

## 4. Issue Lifecycle

```text
status:triage
  -> status:assigned    (Vishwa assigns)
  -> status:in-progress (assigned agent starts)
  -> status:in-qa       (assigned agent hands to Aksha)
  -> status:in-review   (Aksha testing complete)
  -> CLOSED             (Vishwa closes after review/merge)
```

Rules:

- Only Vishwa closes issues.
- Only Aksha moves tested work to `status:in-review`.
- Agents must not skip lifecycle labels.
- Agents must not close their own issues.
- GitHub Issues replace all ad hoc markdown trackers.

---

## 5. Issue Creation Rules

| Agent | Permitted issue types |
|---|---|
| Vishwa, Vastu, Netra | `type:feature`, `type:bug`, `type:task`, `type:chore`, `type:spike` |
| All others | `type:bug`, `type:task`, `type:chore`, `type:spike` |

Parent issue template:

```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue create \
  --title "[Feature] <Title>" \
  --body "## Summary\n<description>\n\n## Acceptance Criteria\n- [ ] <criterion>" \
  --label "type:feature,priority:high,agent:vishwa,status:assigned" \
  --repo venkateshbr/transmuter
```

Sub-issue template:

```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue create \
  --title "[Karya] Implement <Title>" \
  --body "## Task\n<description>\n\nParent: #<id>\n\n## Acceptance Criteria\n- [ ] <criterion>" \
  --label "type:task,priority:high,agent:karya,status:assigned" \
  --repo venkateshbr/transmuter
```

---

## 6. Confidence Gate

- Require at least 95% confidence before modifying code or directing another agent to modify code.
- If below 95%, inspect the repo or ask clarifying questions.
- Vishwa enforces this gate during triage and review.

---

## 7. Acceptance Testing Standard

- Smoke tests do not count as acceptance criteria.
- Mocked API responses do not count as acceptance criteria for product workflows.
- Acceptance requires real API tests against a running API and deterministic seeded sample data.
- Acceptance requires browser UI tests against the real Angular app and real API for user-facing workflows.
- Tests must reset or isolate sample data predictably.
- Tests must not depend on manually created browser state.
- Aksha sign-off must include real sample-data UI/API verification for touched workflows.
- Existing unit tests and TestClient tests may remain as developer checks, but they do not replace real API + browser UI acceptance.

---

## 8. Definition of Done

Backend issues:

- [ ] Acceptance criteria from the GitHub issue are met.
- [ ] Router -> Service -> Repository pattern is followed.
- [ ] All DB queries are tenant-scoped.
- [ ] New tables have RLS.
- [ ] Monetary values use `decimal.Decimal` in Python and string JSON responses.
- [ ] Type hints exist on Python functions.
- [ ] No PII is sent to external LLM APIs.
- [ ] `ruff check` passes or failures are documented as unrelated.
- [ ] Real API tests pass against deterministic sample data.
- [ ] Aksha has signed off.

Frontend issues:

- [ ] Acceptance criteria from the GitHub issue are met.
- [ ] Standalone Angular components only.
- [ ] Routes are lazy-loaded.
- [ ] CSS variable design tokens are used.
- [ ] Light and dark themes are supported.
- [ ] Interactive elements have ARIA labels.
- [ ] Browser UI tests pass against the real app and real API.
- [ ] Aksha has signed off.

All issues:

- [ ] PR is open with `Fixes #<issue_id>` in the body.
- [ ] CI checks are green or documented.
- [ ] Prahari review is complete when triggered.
- [ ] No secrets, credentials, or raw PII are committed.
- [ ] No smoke tests or mock-led tests are used as final acceptance evidence.

---

## 9. PR Protocol

Branch naming:

- `feat/<issue-id>-short-description`
- `fix/<issue-id>-short-description`
- `chore/<issue-id>-short-description`
- `docs/<issue-id>-short-description`

PR requirements:

- Title follows conventional commits.
- Body contains `Fixes #<issue_id>`.
- All CI checks pass before Vishwa merges.
- Aksha sets `status:in-review` before Vishwa merges.
- Squash-merge only to `main`.

---

## 10. Context Loading Tiers

| Tier | Agents | Required context |
|---|---|---|
| Full | Vishwa | GitHub issues, PRD, architecture, design system, test strategy, security review, runbook |
| Broad | Vastu, Netra | Assigned issue, SDLC, PRD, architecture |
| Narrow | Karya, Rupa, Aksha, Chitra, Sthira, Dhruva, Prahari | Assigned issue, SDLC, their role artifact, relevant code |

---

## 11. Prahari Trigger Conditions

Create a Prahari security review issue for:

- Auth, JWT, RLS, RBAC, or tenant isolation changes.
- Agent tools or external API integrations.
- New data classifications or trust boundaries.
- Security-sensitive infrastructure changes.
- Pre-launch security sign-off.

---

## 12. Deprecated Tracking

Do not use:

- `docs/team/STATUS.md`
- `ROADMAP.md`
- `issues.md`
- ad hoc markdown issue lists
- local tracker databases or tracker scripts

Use GitHub Issues exclusively for issue tracking.

---

## Changelog

### 2026-05-02

- Consolidated duplicate SDLC documents into this canonical Transmuter protocol.
- Added founder-approved real sample-data UI/API acceptance testing standard.
- Merged stricter Vishwa-first, lifecycle, DoD, PR, and Prahari rules from the older root protocol.

### 2026-04-30

- Initial Transmuter SDLC created and adapted to the Transmuter domain.
