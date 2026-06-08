# Bankable Plan Sprint-by-Sprint Delivery Plan

> **For Hermes:** execute via issue-first workflow. Keep implementation scoped to the active issue, with GitHub issues as the source of truth.

**Program goal:** deliver a locked bankable-plan baseline on stage-gate approval, then expose frequency-aware benefit realization and mode-aware financial reporting across the product.

**Delivery model:** 4 sprints, each with a clear system boundary, owner, and exit gate. The first sprint starts with backend foundation work; later sprints build on the locked-baseline contract and then propagate it to UI and verification.

---

## Sprint 0 — Plan lock foundation and team routing

**Theme:** establish the execution order, lock the plan contract, and get the backend foundation moving.

**Primary outcome:** the stage-gate approval path can create a locked bankable-plan baseline, and the repo has a clear ownership map for the remaining work.

**Issues in scope**
- `#203` Epic: Bankable plan baseline and benefit realization framework
- `#204` Backend: add bankable plan model and lock-on-approval flow

**Owners / routing**
- `#203` — Vishwa (program owner / issue routing)
- `#204` — Karya (backend implementation)

**Exit criteria**
- Issue #204 is actively in progress.
- The plan lock model is defined enough for downstream benefit tracking.
- The roadmap and sprint breakdown are published for the team.

**Implementation notes**
- Do not mutate approved baselines in place.
- Rebaseline must create a new version and preserve history.
- Any API shape introduced here must be stable enough for Sprint 1/2 consumers.

---

## Sprint 1 — Backend financial contract and frequency-aware benefit ledger

**Theme:** extend the locked baseline into a benefit ledger and config-driven financial model.

**Primary outcome:** the backend can store realized benefits against a locked baseline and can return the correct financial mode metadata for UI consumers.

**Issues in scope**
- `#204` Backend: add bankable plan model and lock-on-approval flow
- `#205` Backend: add benefit realization ledger and frequency rollups
- `#206` Backend: make financial model, scenarios, and rollups configuration-driven

**Owners / routing**
- `#204` — Karya
- `#205` — Karya
- `#206` — Vastu

**Exit criteria**
- Approval → lock path works end-to-end in backend tests.
- Benefit entries can be written and summarized weekly / monthly / yearly.
- APIs return mode metadata and do not assume fixed base/high fields.
- Workbook and dashboard services can read the new mode descriptors without breaking existing consumers.

**Implementation notes**
- Keep the same atomic benefit events; change only the aggregation layer for different frequencies.
- Rollups should be config-driven, not hardcoded to `base` / `high` names.
- Projects without richer scenarios should gracefully degrade to planned-vs-actual.

---

## Sprint 2 — Frontend bankable-plan and benefit-tracking surfaces

**Theme:** expose the new contract to users with dedicated plan and tracking screens.

**Primary outcome:** users can review a locked bankable plan, inspect baseline versions, and track benefits over time, including the stage-gate waterline.

**Issues in scope**
- `#207` Frontend: build bankable plan, benefit tracking, and waterline screens

**Owners / routing**
- `#207` — Rupa (frontend)

**Exit criteria**
- New routes exist for bankable plan, benefit tracking, and waterline views.
- Locked vs editable state is obvious in the UI.
- Weekly / monthly / yearly switching works.
- The waterline visualization clearly shows stage-gate stack vs locked plan line.

**Implementation notes**
- Prefer reuse of existing design tokens and layout primitives.
- Keep new screens separate from existing initiative-editing surfaces where possible.
- Accessibility labels and keyboard navigation should be first-class.

---

## Sprint 3 — Dashboard / control-tower fallback and release hardening

**Theme:** make the rest of the product consume the same financial mode metadata and degrade cleanly when advanced scenarios are absent.

**Primary outcome:** the dashboard, portfolio financials, and control-tower/reporting views all render correctly across project types.

**Issues in scope**
- `#208` Frontend: update dashboard, portfolio financials, and control tower for mode-aware fallback
- `#209` Backend: migration, seeding, and acceptance test coverage for bankable plans

**Owners / routing**
- `#208` — Rupa
- `#209` — Aksha

**Exit criteria**
- Dashboard cards and value bridge adapt to the active financial mode.
- Portfolio financials work for both multi-scenario and planned-vs-actual projects.
- Migration/backfill scripts cover existing data.
- End-to-end acceptance coverage exists for pre-lock and post-lock flows.

**Implementation notes**
- This sprint is the main browser-verification gate before closure.
- Do not assume every project has base/high data.
- If data is missing, preserve layout and show the simpler mode rather than failing.

---

## Recommended execution order

1. Finish `#204` first — it defines the immutable baseline contract.
2. Parallelize `#205` and `#206` only if the shared backend boundaries are stable enough.
3. Start `#207` once the backend contract is settled.
4. Run `#208` and `#209` together near the end so the UI and migration/test coverage verify the same contract.

---

## Program-level checkpoints

- **Checkpoint A:** locked baseline exists and is immutable.
- **Checkpoint B:** weekly / monthly / yearly benefit tracking works.
- **Checkpoint C:** UI surfaces the new model cleanly.
- **Checkpoint D:** dashboards and control tower gracefully degrade when advanced scenarios are absent.
- **Checkpoint E:** migration and acceptance coverage pass before epic closeout.

---

## Suggested labeling / status flow

- `status:assigned` when an issue has an owner but no code started.
- `status:in-progress` when implementation begins.
- `status:in-qa` once the code is done and browser/API verification is underway.
- `status:in-review` when ready for final review / merge.

