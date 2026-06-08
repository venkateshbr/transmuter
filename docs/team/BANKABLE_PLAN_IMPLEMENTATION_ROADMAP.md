# Bankable Plan & Benefit Realization Implementation Roadmap

> **For Hermes:** This roadmap is intended to drive issue creation and phased implementation. Follow the canonical SDLC protocol in `docs/team/SDLC_PROTOCOL.md`.

**Goal:** Add a locked bankable plan at stage-gate approval, then track benefits against that locked baseline at weekly, monthly, and yearly granularity.

**Architecture:** Introduce a versioned, project-scoped financial baseline that is created when the plan gate is approved and then consumed by dashboards, portfolio finance views, workbook exports/imports, and reporting screens. Keep the existing initiative financial model as the editable planning surface, but promote a locked bankable plan snapshot as the immutable reference point for realization tracking and governance.

**Tech Stack:** FastAPI, Supabase/PostgreSQL, Pydantic, Angular 18, Tailwind/CSS variables, existing financial services, existing dashboard/reporting services.

---

## 1) Current-State Inventory

### Existing strengths
- Stage-gate workflow already exists (`L0`–`L5`) with approval steps.
- Initiative financial detail already exists, including scenario-style fields, cost lines, workbook import/export, and value bridge logic.
- Portfolio financial dashboards already exist.
- Executive control tower and dashboard reporting already exist.
- Shared cost pools and allocation runs already exist.
- Financial configuration already exists at tenant level.

### Current limitations
- The platform does **not** yet model a first-class **bankable plan** snapshot.
- There is no explicit **lock-on-approval** behavior when the plan gate is approved.
- Benefit tracking is not yet organized around a locked baseline with frequency-aware realization.
- Dashboard and reporting layers still assume a mostly fixed financial model.
- Base/high/actual is still too hardcoded in several paths.
- Project-specific P&L line config is not fully distinct from tenant-level config.

---

## 2) Gap Analysis

### Requirement A — Lock the bankable plan on approval
**Need:** When the stage-gate plan is approved, freeze a baseline that becomes the source of truth for future tracking.

**Gap today:**
- The stage-gate approval flow does not create a locked baseline artifact.
- The approval event is not linked to a versioned financial snapshot.

**Outcome required:**
- Create a lockable, versioned bankable plan.
- Preserve audit history.
- Support formal rebaseline only.

### Requirement B — Track benefits weekly, monthly, yearly
**Need:** A single initiative benefit model must roll up to weekly, monthly, and yearly views.

**Gap today:**
- Benefit data is not clearly modeled as a realization ledger with frequency metadata.
- Aggregation logic is not first-class and not governance-aware.

**Outcome required:**
- Add frequency-aware benefit entries.
- Aggregate by period in backend services.
- Allow the UI to switch frequency without changing the underlying model.

### Requirement C — Dynamic scenario / financial model
**Need:** Support projects that have:
- base/high/actual
- only one planned value + actual
- future custom cases

**Gap today:**
- Several screens and services still assume base/high/actual.
- Rollup logic is not fully driven by configuration.

**Outcome required:**
- Mode-aware financial summaries.
- Graceful fallback to planned vs actual when no additional cases exist.
- Configurable case definitions per project.

### Requirement D — Dynamic rollups and configurable P&L lines
**Need:** Project-specific P&L definitions and rollup rules.

**Gap today:**
- Tenant-level config exists, but project override and line definition are incomplete.
- Hardcoded metrics still leak into dashboards and workbook generation.

**Outcome required:**
- Tenant default financial template.
- Project override model.
- Rollup designer.
- Config-driven workbook and summary generation.

### Requirement E — Waterline / above-below baseline reporting
**Need:** Show below-waterline pipeline value vs above-waterline bankable value.

**Gap today:**
- No dedicated waterline view.
- No visible distinction between planned pipeline and banked value.

**Outcome required:**
- A dedicated waterline UI and API.
- Stage-gate and benefit trend views that reflect the locked plan.

---

## 3) Target Product Model

### Core concepts
1. **Financial Template**
   - Tenant default set of metrics, cost categories, rollups, and scenario definitions.

2. **Project Financial Model**
   - Initiative-level override of the template.
   - Defines which P&L lines, case columns, and rollups are active.

3. **Bankable Plan**
   - The approved baseline created at plan-gate approval.
   - Versioned and immutable until rebaseline.

4. **Benefit Realization Ledger**
   - Weekly/monthly/yearly realization data linked to the bankable plan.

5. **Mode-aware Reporting**
   - If advanced cases exist, show multi-case reporting.
   - If not, degrade to planned vs actual everywhere.

---

## 4) Screen-by-Screen Plan

### 4.1 Dashboard
**Existing route:** `/dashboard`

**Current role:** Executive landing page.

**New behavior:**
- Show whether the initiative/portfolio is in pre-lock or post-lock mode.
- Display locked plan vs realized benefits.
- Support weekly/monthly/yearly benefit trend views.
- Auto-degrade to planned vs actual if project cases are not defined.

**New UI elements:**
- Bankable plan status card
- Waterline widget
- Benefit trend toggle
- Locked baseline date/version indicator

---

### 4.2 Initiative Financial Detail
**Existing route:** initiative detail financial tab.

**Current role:** Financial grid editing and workbook-style entry.

**New behavior:**
- Remains the editing surface before lock.
- Switches to read-focused baseline review after lock.
- Supports “create bankable plan snapshot” actions.
- Displays scenario configuration and frequency-aware benefit views.

**New UI elements:**
- Lock status banner
- Create/refresh bankable plan button
- Baseline version history drawer
- Benefit tracking sub-tab

---

### 4.3 Financial Scope / Project P&L Builder
**Existing route:** `/initiatives/:id/financial-scope`

**Current role:** Selecting active metrics and cost categories.

**New behavior:**
- Evolve into a project financial model builder.
- Allow case definitions and P&L line mapping.
- Allow project-specific overrides from tenant defaults.

**New UI elements:**
- Case configuration section
- P&L line mapping section
- Rollup mapping section
- Inheritance / override indicators

---

### 4.4 New Screen: Bankable Plan
**Purpose:** Review the locked baseline.

**Contains:**
- baseline summary
- approval metadata
- lock version
- immutable plan snapshot
- rebaseline history
- comparison against current actuals

---

### 4.5 New Screen: Benefit Tracking
**Purpose:** Capture and review benefit realization.

**Contains:**
- period switcher (weekly / monthly / yearly)
- benefit ledger entries
- actual vs locked plan comparison
- variance trend
- comments / evidence attachments if needed later

---

### 4.6 New Screen: Stage-Gate Waterline View
**Purpose:** Show the waterline concept from the reference page.

**Contains:**
- stage-gate stack (L1–L5)
- locked bankable plan line
- realized benefits trend line
- period selector
- visible pre-lock vs post-lock distinction

---

### 4.7 Portfolio Financials
**Existing route:** `/financials`

**Current role:** Portfolio-wide planned vs actual financials.

**New behavior:**
- Use the same configuration-driven rollup engine.
- Automatically adapt columns based on active cases.
- Fallback to simple planned vs actual when advanced cases are absent.

---

### 4.8 Executive Control Tower / Reports
**Existing route:** `/reports/control-tower`

**New behavior:**
- Ensure all persona reports read from the locked baseline and realization ledger.
- Keep report-specific layouts, but not report-specific financial logic.

---

## 5) API-by-API Plan

### Existing APIs to extend
- `GET /initiatives/{id}/financials`
- `PUT /initiatives/{id}/financials`
- `GET /initiatives/{id}/financials/selections`
- `PUT /initiatives/{id}/financials/selections`
- `GET /portfolio/financials`
- `GET /dashboard`
- `GET /admin/financial-configuration`
- `PUT /admin/financial-configuration`
- workbook import/export endpoints
- stage-gate approval endpoints

### New APIs to add

#### Bankable plan
- `GET /initiatives/{id}/bankable-plan`
- `POST /initiatives/{id}/bankable-plan/lock`
- `POST /initiatives/{id}/bankable-plan/rebaseline`
- `GET /initiatives/{id}/bankable-plan/history`

#### Benefit realization
- `GET /initiatives/{id}/benefits?granularity=weekly|monthly|yearly`
- `PUT /initiatives/{id}/benefits`
- `GET /initiatives/{id}/benefits/summary`

#### Financial model / scenarios
- `GET /initiatives/{id}/financial-model`
- `PUT /initiatives/{id}/financial-model`
- `GET /financial-models/default`
- `PUT /financial-models/default`
- `GET /initiatives/{id}/financial-scenarios`
- `PUT /initiatives/{id}/financial-scenarios`

#### Rollups
- `GET /financial-rollups`
- `PUT /financial-rollups`
- `GET /initiatives/{id}/financial-rollups`
- `PUT /initiatives/{id}/financial-rollups`

#### Waterline reporting
- `GET /initiatives/{id}/waterline`
- `GET /portfolio/waterline`

### API behavior rules
- All financial summaries must include a `financial_mode` descriptor.
- If only one plan case exists, return planned vs actual mode.
- If multiple cases exist, return scenario-aware mode.
- If no bankable plan exists yet, return pre-lock planning mode.

---

## 6) Data Model Changes

### New tables / entities to introduce
- `financial_templates`
- `financial_template_groups`
- `financial_template_items`
- `financial_template_scenarios`
- `initiative_financial_models`
- `initiative_financial_model_items`
- `initiative_bankable_plans`
- `initiative_bankable_plan_versions`
- `benefit_realization_entries`
- `benefit_realization_rollups`
- `financial_rollup_rules`

### Required properties
- `tenant_id` on every table
- `initiative_id` where project-scoped
- `version_number` for locked plans
- `status` values such as `draft`, `approved`, `locked`, `rebaselined`, `superseded`
- `granularity` on benefit realization entries
- `effective_from` / `effective_to` where useful

### Key invariants
- A locked bankable plan must not be edited directly.
- Rebaseline creates a new version.
- Historical versions remain queryable.
- Rollup rules must be deterministic.

---

## 7) Implementation Phases

### Phase 1 — Design and data model
**Deliverables:**
- bankable plan schema
- benefit realization schema
- financial model template/override schema
- rollup rules schema

**Acceptance:**
- schema supports lock/rebaseline/history/frequency aggregation

### Phase 2 — Backend services and APIs
**Deliverables:**
- bankable plan lock service
- benefit aggregation service
- scenario/mode resolver
- rollup engine
- waterline endpoints

**Acceptance:**
- APIs return mode-aware financial payloads
- lock-on-approval is functional

### Phase 3 — Frontend screen updates
**Deliverables:**
- bankable plan screen
- benefit tracking screen
- waterline screen
- project financial model builder updates
- dashboard fallback UI updates

**Acceptance:**
- user can lock a plan, see the locked baseline, and track realized benefits by frequency

### Phase 4 — Workbook and reporting integration
**Deliverables:**
- config-driven workbook import/export
- portfolio financials updated for mode awareness
- executive reporting updated for locked plan behavior

**Acceptance:**
- exports/imports respect the active project model
- dashboards don’t break when base/high are absent

### Phase 5 — Migration and cleanup
**Deliverables:**
- seed default templates from current configuration
- backfill existing initiatives into bankable plan mode where possible
- compatibility shims for old data patterns

**Acceptance:**
- existing tenants continue to work without manual data repair

---

## 8) Suggested GitHub Issue Breakdown

### Epic
- **#203** — Bankable plan baseline and benefit realization framework

### Sub-issues
- **#204** — Backend: add bankable plan model and lock-on-approval flow
- **#205** — Backend: add benefit realization ledger and frequency rollups
- **#206** — Backend: make financial model, scenarios, and rollups configuration-driven
- **#207** — Frontend: build bankable plan, benefit tracking, and waterline screens
- **#208** — Frontend: update dashboard, portfolio financials, and control tower for mode-aware fallback
- **#209** — Backend: migration, seeding, and acceptance test coverage for bankable plans

### Notes
- The roadmap doc is the shared implementation reference for all six child issues.
- The epic issue should remain open until all sub-issues are in review or merged and acceptance is complete.

---

## 9) Acceptance Criteria for the Release

- [ ] A plan gate approval creates a locked bankable baseline.
- [ ] Locked baselines are versioned and immutable.
- [ ] Benefits can be tracked weekly, monthly, and yearly.
- [ ] Dashboards degrade gracefully to planned vs actual when advanced cases are absent.
- [ ] Project financial P&L lines can differ by project.
- [ ] Rollups are driven by configuration, not hardcoded field names.
- [ ] Workbook import/export respects the active financial model.
- [ ] Existing projects remain functional during migration.

---

## 10) Out of Scope for this Release
- Peer benchmarking against external organizations.
- Full McKinsey-style advisory services workflow.
- New investor portal or external client portal.
- Advanced forecasting beyond the locked-plan / realization framework.

---

## 11) Recommended Next Step Order
1. Finalize the financial model / bankable plan schema.
2. Create the backend issue set.
3. Implement lock-on-approval.
4. Implement benefit realization aggregation.
5. Build the new screens.
6. Update dashboards and workbook exports.
7. Run real API + browser verification.
8. Merge after acceptance.

---

## 12) Notes for implementers
- Keep the existing editable financial grid as the pre-lock planning surface.
- Do not hardcode base/high/actual into new code paths.
- Treat the locked bankable plan as the source of truth after approval.
- Preserve all prior versions for audit and rebaseline review.
- Use the same financial mode resolver across dashboard, portfolio, and report screens.
