# SDLC Protocol — Transmuter
**Owner**: Vishwa | **Status**: Living Document | **Last Updated**: 2026-04-30

## The Single Source of Truth

GitHub Issues at **https://github.com/venkateshbr/transmuter** are the single source of truth for all work. Nothing gets built without a ticket.

---

## 1. Mandatory First Step (Every Task)

Every agent, every time, before doing any work:

1. Check assigned issues: `gh issue list --label "agent:<name>" --state open --repo venkateshbr/transmuter`
2. Find your issue — confirm status is `assigned`
3. Set to `in-progress`: `gh issue edit <id> --add-label "status:in-progress" --repo venkateshbr/transmuter`
4. Do the work
5. When complete, set to `in-qa`: `gh issue edit <id> --remove-label "status:in-progress" --add-label "status:in-qa" --repo venkateshbr/transmuter`

---

## 2. Vishwa-First Protocol

ALL requests from the founder route through Vishwa:

1. **Vishwa** receives the request, analyzes scope, creates a parent issue
2. **Vishwa** decomposes into sub-issues and assigns to specialists
3. **Specialists** execute in order (see §3)
4. **Vishwa** reviews all output before marking complete and presenting to founder

Vishwa seeks **founder approval** before any non-trivial action. No agent self-starts.

---

## 3. Agent Execution Order

### Full Feature Pipeline
```
Netra (requirements + user stories)
  ↓
Vastu (architecture + schema design)
  ↓
Chitra (UI/UX design spec)
  ↓
Karya + Rupa (backend + frontend — parallel where possible)
  ↓
Aksha (tests + evals)
  ↓
Sthira (CI/CD + infra)
  ↓
Vishwa (final review + PR merge + issue close)
```

**Prahari (Security)** is triggered before `in-review` for any PR touching: auth, RLS, JWT, agent tools, external integrations.

### Shortcuts
- **Bug fix** → assign directly to Karya (backend) or Rupa (frontend)
- **UI-only change** → Chitra (design) → Rupa (implement) → Aksha (test)
- **Backend-only change** → Karya (implement) → Aksha (test)
- **Infrastructure/CI change** → Sthira

---

## 4. Issue Lifecycle

```
status:triage
  → status:assigned    (Vishwa assigns to agent)
  → status:in-progress (agent starts work)
  → status:in-qa       (agent hands to Aksha)
  → status:in-review   (Vishwa reviews PR)
  → CLOSED             (Vishwa closes after PR merge)
```

**Only Vishwa closes issues.** All agents transition up to `in-qa`.

---

## 5. Issue Creation Rules

| Agent | Permitted Issue Types |
|---|---|
| Vishwa, Vastu, Netra | `feature`, `bug`, `task`, `chore`, `spike` |
| All others | `bug`, `task`, `chore`, `spike` only |

### Parent Issue Template
```
gh issue create \
  --title "[Feature] <Title>" \
  --body "## Summary\n<description>\n\n## Acceptance Criteria\n- [ ] <criterion>" \
  --label "type:feature,priority:high,agent:vishwa" \
  --repo venkateshbr/transmuter
```

### Sub-Issue Template
```
gh issue create \
  --title "[Karya] Implement <Title>" \
  --body "## Task\n<description>\n\nParent: #<id>\n\n## AC\n- [ ] <criterion>" \
  --label "type:task,priority:high,agent:karya,status:assigned" \
  --repo venkateshbr/transmuter
```

---

## 6. Confidence Gate

- **≥95% confidence** required before any agent modifies code or directs another agent to
- If < 95%, ask clarifying questions until reached
- Vishwa enforces this gate during review

---

## 7. PR Protocol

Branch naming:
- `feat/<short-description>` — new feature
- `fix/<short-description>` — bug fix
- `chore/<short-description>` — maintenance
- `docs/<short-description>` — documentation

PR requirements:
- Title references the issue: `feat: <title> (#<id>)`
- `Fixes #<issue_id>` in body
- All CI checks passing
- Prahari review complete (if security-relevant)
- Squash-merge only to `main`

---

## 8. Definition of Done

### Backend (Karya)
- [ ] Decimal for all monetary values
- [ ] All queries tenant-scoped
- [ ] RLS enforced on new tables
- [ ] Service layer pattern followed
- [ ] Type hints on all functions
- [ ] No PII sent to LLM APIs
- [ ] Tests passing (Aksha sign-off)

### Frontend (Rupa)
- [ ] Works in both light and dark themes
- [ ] Uses CSS variable design tokens
- [ ] Standalone component (no NgModules)
- [ ] Lazy-loaded route
- [ ] ARIA labels present

### AI / Agent (Karya + Netra)
- [ ] Langfuse trace attached
- [ ] HITL checkpoint in place
- [ ] Eval dataset entry added
- [ ] Graceful degradation handled (agent failure doesn't crash UI)

---

## 9. Context Loading Tiers

| Tier | Agents | What They Load |
|---|---|---|
| Full | Vishwa | All team artifacts + GitHub issues |
| Broad | Vastu, Netra | Architecture + PRD + assigned issues |
| Narrow | Karya, Rupa, Aksha, Chitra, Sthira, Dhruva | Their artifact + SDLC + assigned issues |

---

## 10. Prahari Trigger Conditions

Call Prahari (create a `[Prahari]` sub-issue) for:
- Any feature touching auth, JWT, RLS, RBAC
- New agent tool or external API integration
- New tenant or data classification introduced
- Quarterly audit
- Pre-launch security sign-off

---

## Changelog

### 2026-04-30 — Initial creation
- Adapted from Aethos SDLC_PROTOCOL.md for Transmuter domain
- Updated all artifact paths and GitHub repo references
- Added agent spec references to new YAML format
