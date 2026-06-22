import { Component, WritableSignal, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';

interface WorkstreamOption {
  id: string;
  name: string;
}

interface BusinessUnitOption {
  id: string;
  name: string;
}

interface UserOption {
  id: string;
  display_name: string;
}

interface FinancialConfigGroup {
  key: string;
  label: string;
  kind: 'calculation' | 'metric' | 'cost_category';
  display_order: number;
  is_active: boolean;
}

interface FinancialConfigItem {
  key: string;
  label: string;
  item_type: 'metric' | 'cost_category';
  system_metric_key?: string | null;
  rollup_type?: string | null;
  group_key?: string | null;
  display_order: number;
  is_active: boolean;
}

interface FinancialConfiguration {
  groups: FinancialConfigGroup[];
  items: FinancialConfigItem[];
}

type CreationPath = 'chooser' | 'form' | 'upload' | 'ai';

@Component({
  selector: 'app-create-initiative',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  styles: [`
    :host { display: block; }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .animate-in { animation: fadeIn 0.3s ease both; }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .slide-up { animation: slideUp 0.35s ease both; }

    .path-card {
      cursor: pointer;
      transition: all 0.25s ease;
      position: relative;
      overflow: hidden;
    }
    .path-card::before {
      content: '';
      position: absolute;
      inset: 0;
      background: var(--t-accent-gradient);
      opacity: 0;
      transition: opacity 0.25s ease;
      border-radius: inherit;
    }
    .path-card:hover::before { opacity: 0.04; }
    .path-card:hover {
      border-color: var(--t-accent);
      box-shadow: 0 8px 24px var(--t-accent-ring);
      transform: translateY(-2px);
    }

    .field-label {
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.375rem;
      color: var(--t-text-secondary);
    }

    .step-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .step-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      transition: all 0.2s ease;
    }
    .step-dot.active {
      background: var(--t-accent);
      box-shadow: 0 0 0 3px var(--t-accent-ring);
    }
    .step-dot.complete { background: var(--t-green); }
    .step-dot.pending {
      background: var(--t-border);
    }

    select {
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
      padding-right: 30px !important;
    }

    textarea { resize: vertical; min-height: 80px; }

    .upload-zone {
      border: 2px dashed var(--t-border);
      border-radius: 12px;
      padding: 3rem 2rem;
      text-align: center;
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .upload-zone:hover,
    .upload-zone.dragover {
      border-color: var(--t-accent);
      background: var(--t-accent-soft);
    }
  `],
  template: `
<div class="min-h-screen" style="background:var(--t-bg)">
  <div class="max-w-4xl mx-auto px-8 py-8">

    <!-- BREADCRUMB -->
    <div class="flex items-center gap-2 mb-6 text-sm animate-in">
      <a routerLink="/initiatives/pipeline"
         class="transition-colors"
         style="color:var(--t-text-secondary)"
         aria-label="Back to pipeline">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </a>
      <a routerLink="/initiatives/pipeline"
         style="color:var(--t-text-secondary)"
         class="hover:underline">Initiatives</a>
      <span style="color:var(--t-border)">/</span>
      <span style="color:var(--t-text-primary)" class="font-medium">{{ editId ? 'Edit Initiative' : 'New Initiative' }}</span>
    </div>

    <!-- ═══════════════ PATH CHOOSER ═══════════════ -->
    <div *ngIf="currentPath === 'chooser'" class="slide-up">
      <h1 class="text-3xl font-bold tracking-tight mb-2"
          style="color:var(--t-text-primary)">
        Create Initiative<span style="color:var(--t-accent)">.</span>
      </h1>
        <p class="mb-8" style="color:var(--t-text-secondary)">
        Choose how you'd like to create your initiative.
      </p>

      <div *ngIf="!editId && isCreationBlocked()" class="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-amber-600">Tenant setup required</p>
            <h2 class="mt-1 text-lg font-black" style="color:var(--t-text-primary)">Configure the tenant before creating initiatives</h2>
            <p class="mt-2 max-w-3xl text-sm leading-6" style="color:var(--t-text-secondary)">
              Complete the setup checklist in Admin first. That includes business units, workstreams,
              financial engine definitions, stage gates, and gate criteria.
            </p>
          </div>
          <a routerLink="/admin" class="btn-primary px-4 py-2 text-[10px] font-black uppercase tracking-widest" aria-label="Open tenant administration setup">
            Open Admin
          </a>
        </div>
        <div *ngIf="setupStatus().checks?.length" class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div *ngFor="let check of setupStatus().checks || []" class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3">
            <p class="text-[9px] font-black uppercase tracking-widest" [class.text-emerald-600]="check.complete" [class.text-amber-600]="!check.complete">
              {{ check.complete ? 'Complete' : 'Open' }}
            </p>
            <p class="mt-1 text-xs font-black text-[var(--t-text-primary)]">{{ check.label }}</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

        <!-- Path A: Guided Form -->
        <div class="card path-card p-6" (click)="currentPath = 'form'"
             role="button" tabindex="0" aria-label="Create initiative with Transmuter"
             (keydown.enter)="currentPath = 'form'">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
               style="background:var(--t-accent-soft)">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold mb-2" style="color:var(--t-text-primary)">
            Create with Transmuter
          </h3>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            Use a guided intake flow with reviewable defaults for scope, value logic, and delivery ownership.
          </p>
        </div>

        <!-- Path B: Excel Upload -->
        <div class="card path-card p-6" (click)="currentPath = 'upload'"
             role="button" tabindex="0" aria-label="Upload Excel template"
             (keydown.enter)="currentPath = 'upload'">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
               style="background:rgba(16,185,129,0.08)">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>
              <line x1="12" x2="12" y1="3" y2="15"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold mb-2" style="color:var(--t-text-primary)">
            Upload Excel Template
          </h3>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            Upload a pre-filled Transmuter Excel template with all initiative data.
          </p>
          <button class="text-xs mt-3 inline-block underline"
                  style="color:var(--t-accent)"
                  (click)="downloadTemplate($event)"
                  aria-label="Download blank initiative template">
            Download blank template
          </button>
        </div>
      </div>
    </div>

    <!-- ═══════════════ MANUAL FORM ═══════════════ -->
    <div *ngIf="currentPath === 'form'" class="slide-up">
      <div *ngIf="!editId && isCreationBlocked()" class="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
        <p class="text-[10px] font-black uppercase tracking-widest text-amber-600">Tenant setup required</p>
        <p class="mt-2 text-sm font-bold text-[var(--t-text-primary)]">This tenant must finish setup before a new initiative can be created.</p>
        <p class="mt-1 text-sm leading-6 text-[var(--t-text-secondary)]">
          Open Admin and complete the missing setup checks first. New initiative creation is intentionally blocked until the setup checklist is complete.
        </p>
      </div>

      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-3xl font-bold tracking-tight"
              style="color:var(--t-text-primary)">
            {{ editId ? 'Edit Initiative' : 'New Initiative' }}<span style="color:var(--t-accent)">.</span>
          </h1>
          <p class="text-sm mt-1" style="color:var(--t-text-secondary)">
            Step {{ formStep }} of {{ editId ? 3 : 4 }} — {{ stepLabel() }}
          </p>
        </div>
        <div class="step-indicator">
          <div *ngFor="let s of totalSteps()"
               class="step-dot"
               [class.active]="formStep === s"
               [class.complete]="formStep > s"
               [class.pending]="formStep < s">
          </div>
        </div>
      </div>

      <div class="card p-6">
        <div class="mb-5 rounded-xl border p-4 flex items-start gap-3"
             style="background:var(--t-accent-soft);border-color:var(--t-border)">
          <span class="material-icons text-base mt-0.5" style="color:var(--t-accent)">auto_awesome</span>
          <div>
            <p class="text-xs font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-primary)">{{ editId ? 'Edit mode' : 'Transmuter intake' }}</p>
            <p class="text-sm" style="color:var(--t-text-secondary)">
              {{ editId
                ? 'Update core initiative fields. Financials, KPIs, risks, and milestones stay managed from their dedicated tabs.'
                : 'Capture the case, then review AI-assisted financial, KPI, risk, and milestone suggestions before creation.' }}
            </p>
          </div>
        </div>

        <!-- STEP 1: Basic Details -->
        <div *ngIf="formStep === 1" class="space-y-5 animate-in">
          <div>
            <label for="init-name" class="field-label">Initiative Name *</label>
            <input id="init-name" type="text" class="input-field"
                   [(ngModel)]="form.name" placeholder="e.g. HK Accounting System Integration & Automation"
                   aria-required="true">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-workstream" class="field-label">Workstream</label>
              <select id="init-workstream" class="input-field" [(ngModel)]="form.workstream_id">
                <option value="">Select workstream</option>
                <option *ngFor="let ws of workstreams()" [value]="ws.id">{{ ws.name }}</option>
              </select>
            </div>
            <div>
              <p class="field-label">Impacted Business Units</p>
              <div class="max-h-36 overflow-auto border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                <label *ngFor="let bu of businessUnits()" class="flex items-center gap-2 py-1 text-sm font-bold text-[var(--t-text-primary)]">
                  <input
                    type="checkbox"
                    class="h-4 w-4 border border-[var(--t-border)]"
                    [checked]="isBusinessUnitSelected(bu.id)"
                    (change)="toggleBusinessUnit(bu.id, $any($event.target).checked)"
                    [attr.aria-label]="'Toggle business unit ' + bu.name">
                  <span>{{ bu.name }}</span>
                </label>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-country" class="field-label">Market</label>
              <select id="init-country" class="input-field" [(ngModel)]="form.country">
                <option value="">Select market</option>
                <option *ngFor="let market of marketOptions()" [value]="market">{{ market }}</option>
              </select>
            </div>
            <div>
              <label for="init-theme" class="field-label">Theme</label>
              <select id="init-theme" class="input-field" [(ngModel)]="form.theme">
                <option value="">Select theme</option>
                <option *ngFor="let theme of themeOptions()" [value]="theme">{{ theme }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-type" class="field-label">Initiative Type</label>
              <select id="init-type" class="input-field" [(ngModel)]="form.type">
                <option value="">Select type</option>
                <option value="revenue_growth">Revenue Growth</option>
                <option value="cost_reduction">Cost Reduction</option>
                <option value="cost_avoidance">Cost Avoidance</option>
                <option value="compliance">Compliance</option>
                <option value="capability_building">Capability Building</option>
              </select>
            </div>
            <div>
              <label for="init-impact" class="field-label">Impact Type</label>
              <select id="init-impact" class="input-field" [(ngModel)]="form.impact_type">
                <option value="">Select impact</option>
                <option value="recurring">Recurring</option>
                <option value="one_off">One-off</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-priority" class="field-label">Priority</label>
              <select id="init-priority" class="input-field" [(ngModel)]="form.priority">
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label for="init-tag" class="field-label">Tag</label>
              <select id="init-tag" class="input-field" [(ngModel)]="form.tag">
                <option value="">Select tag</option>
                <option *ngFor="let tag of tagOptions()" [value]="tag">{{ labelize(tag) }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- STEP 2: Description & Context -->
        <div *ngIf="formStep === 2" class="space-y-5 animate-in">
          <div>
            <label for="init-summary" class="field-label">Summary / Description</label>
            <textarea id="init-summary" class="input-field" rows="3"
                      [(ngModel)]="form.summary"
                      placeholder="End-to-end accounting process automation..."></textarea>
          </div>

          <div>
            <label for="init-context-problem" class="field-label">Context & Problem</label>
            <textarea id="init-context-problem" class="input-field" rows="3"
                      [(ngModel)]="form.context_problem"
                      placeholder="Current pain points, operating context, and why this initiative matters..."></textarea>
          </div>

          <div>
            <label for="init-value-logic" class="field-label">Value Logic / Main Assumptions</label>
            <textarea id="init-value-logic" class="input-field" rows="3"
                      [(ngModel)]="form.value_logic"
                      placeholder="25–30% productivity uplift through system integration..."></textarea>
          </div>

          <div>
            <label for="init-deps" class="field-label">Dependencies</label>
            <textarea id="init-deps" class="input-field" rows="2"
                      [(ngModel)]="form.dependencies_text"
                      placeholder="Any upstream or downstream dependencies..."></textarea>
          </div>
        </div>

        <!-- STEP 3: Ownership & Timeline -->
        <div *ngIf="formStep === 3" class="space-y-5 animate-in">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-owner" class="field-label">Market Owner</label>
              <select id="init-owner" class="input-field" [(ngModel)]="form.owner_id">
                <option value="">Select owner</option>
                <option *ngFor="let u of users()" [value]="u.id">{{ u.display_name }}</option>
              </select>
            </div>
            <div>
              <label for="init-group-owner" class="field-label">Group Owner</label>
              <select id="init-group-owner" class="input-field" [(ngModel)]="form.group_owner_id">
                <option value="">Select group owner</option>
                <option *ngFor="let u of users()" [value]="u.id">{{ u.display_name }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="init-start" class="field-label">Planned Start Date</label>
              <input id="init-start" type="date" class="input-field"
                     [(ngModel)]="form.planned_start">
            </div>
            <div>
              <label for="init-end" class="field-label">Planned Completion Date</label>
              <input id="init-end" type="date" class="input-field"
                     [(ngModel)]="form.planned_end">
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
            <div *ngIf="financialSelectionsLocked()" class="lg:col-span-2 border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3 text-sm" style="color:var(--t-text-secondary)">
              <span class="font-bold" style="color:var(--t-text-primary)">Financial values locked.</span>
              Scope selections can still be saved by the transformation office.
            </div>
            <section class="rounded-lg border p-4" style="border-color:var(--t-border);background:var(--t-bg)">
              <div class="mb-3">
                <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">Financial Metrics</p>
                <h3 class="text-sm font-bold" style="color:var(--t-text-primary)">Shown in Initiative Financials</h3>
              </div>
              <div class="space-y-2 max-h-56 overflow-auto pr-1">
                <label *ngFor="let metric of financialMetricOptions()"
                       class="flex items-center gap-3 rounded border px-3 py-2 text-sm"
                       style="border-color:var(--t-border);color:var(--t-text-primary)">
                  <input type="checkbox"
                         [checked]="isMetricSelected(metric)"
                         (change)="toggleMetric(metric, $any($event.target).checked)"
                         aria-label="Toggle financial metric">
                  <span class="min-w-0 flex-1 truncate">{{ metric.label }}</span>
                </label>
              </div>
            </section>

            <section class="rounded-lg border p-4" style="border-color:var(--t-border);background:var(--t-bg)">
              <div class="mb-3">
                <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">Cost Categories</p>
                <h3 class="text-sm font-bold" style="color:var(--t-text-primary)">One-time and recurring cost rows</h3>
              </div>
              <div class="space-y-2 max-h-56 overflow-auto pr-1">
                <label *ngFor="let cost of costCategoryOptions()"
                       class="flex items-center gap-3 rounded border px-3 py-2 text-sm"
                       style="border-color:var(--t-border);color:var(--t-text-primary)">
                  <input type="checkbox"
                         [checked]="isCostCategorySelected(cost)"
                         (change)="toggleCostCategory(cost, $any($event.target).checked)"
                         aria-label="Toggle cost category">
                  <span class="min-w-0 flex-1 truncate">{{ cost.label }}</span>
                  <span class="text-[10px] font-bold uppercase" style="color:var(--t-text-tertiary)">
                    {{ cost.rollup_type === 'recurring_cost' ? 'Recurring' : 'One-time' }}
                  </span>
                </label>
              </div>
            </section>

            <section class="lg:col-span-2 rounded-lg border p-4" style="border-color:var(--t-border);background:var(--t-bg)" data-testid="initiative-edit-annual-baseline">
              <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">Annual Baseline</p>
                  <h3 class="text-sm font-bold" style="color:var(--t-text-primary)">Original operating metrics</h3>
                </div>
                <div class="w-32">
                  <label for="init-baseline-year" class="field-label">Fiscal Year</label>
                  <input
                    id="init-baseline-year"
                    type="number"
                    min="2020"
                    max="2060"
                    class="input-field"
                    [disabled]="baselineLocked()"
                    [(ngModel)]="form.baseline_year"
                    aria-label="Baseline fiscal year">
                </div>
              </div>
              <div *ngIf="baselineLocked()" class="mb-3 border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3 text-sm" style="color:var(--t-text-secondary)">
                <span class="font-bold" style="color:var(--t-text-primary)">Annual baseline locked.</span>
                {{ baselineLockReason() || 'Baseline updates are locked by governance.' }}
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                <label *ngFor="let metric of baselineMetricOptions()"
                       class="block rounded border px-3 py-2"
                       style="border-color:var(--t-border);color:var(--t-text-primary)">
                  <span class="block truncate text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">{{ metric.label }}</span>
                  <input
                    type="number"
                    class="input-field mt-2"
                    [disabled]="baselineLocked()"
                    [ngModel]="baselineMetricValue(metric.id)"
                    (ngModelChange)="setBaselineMetricValue(metric.id, $event)"
                    [attr.aria-label]="'Annual baseline value for ' + metric.label">
                </label>
              </div>
            </section>
          </div>
        </div>

        <!-- STEP 4: HITL Suggestions -->
        <div *ngIf="formStep === 4" class="space-y-5 animate-in">
          <div class="rounded-xl border p-4" style="border-color:var(--t-border);background:var(--t-bg)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">HITL Review</p>
                <h3 class="text-lg font-bold" style="color:var(--t-text-primary)">Transmuter suggestions</h3>
                <p class="text-sm mt-1" style="color:var(--t-text-secondary)">
                  Accept, reject, or edit each suggestion before committing to the database.
                </p>
              </div>
              <span class="text-[10px] font-bold uppercase rounded-full px-2 py-1"
                    style="background:var(--t-accent-soft);color:var(--t-accent)">
                {{ suggestions()?.agent_status || 'pending' }}
              </span>
            </div>
          </div>

          <div *ngIf="suggestions() as suggestionSet" class="grid grid-cols-1 gap-4">
            <section class="card p-4">
              <h4 class="text-sm font-bold mb-3" style="color:var(--t-text-primary)">Financials</h4>
              <label *ngFor="let item of suggestionSet.financial_entries; let i = index"
                     class="grid grid-cols-[auto_1fr_1fr] gap-3 items-center mb-2">
                <input type="checkbox" [(ngModel)]="item.accepted" aria-label="Accept financial suggestion">
                <input class="input-field text-xs" [(ngModel)]="item.gm_uplift_base" aria-label="Suggested base value">
                <input class="input-field text-xs" [(ngModel)]="item.gm_uplift_high" aria-label="Suggested high value">
              </label>
              <label *ngFor="let item of suggestionSet.cost_lines; let i = index"
                     class="grid grid-cols-[auto_1fr_1fr] gap-3 items-center mb-2">
                <input type="checkbox" [(ngModel)]="item.accepted" aria-label="Accept cost suggestion">
                <input class="input-field text-xs" [(ngModel)]="item.name" aria-label="Suggested cost name">
                <input class="input-field text-xs" [(ngModel)]="item.amount_plan" aria-label="Suggested cost amount">
              </label>
            </section>

            <section class="card p-4">
              <h4 class="text-sm font-bold mb-3" style="color:var(--t-text-primary)">KPIs</h4>
              <label *ngFor="let item of suggestionSet.kpis"
                     class="grid grid-cols-[auto_1fr_120px] gap-3 items-center mb-2">
                <input type="checkbox" [(ngModel)]="item.accepted" aria-label="Accept KPI suggestion">
                <input class="input-field text-xs" [(ngModel)]="item.name" aria-label="Suggested KPI name">
                <input class="input-field text-xs" [(ngModel)]="item.unit" aria-label="Suggested KPI unit">
              </label>
            </section>

            <section class="card p-4">
              <h4 class="text-sm font-bold mb-3" style="color:var(--t-text-primary)">Risks</h4>
              <label *ngFor="let item of suggestionSet.risks"
                     class="grid grid-cols-[auto_1fr_120px_120px] gap-3 items-center mb-2">
                <input type="checkbox" [(ngModel)]="item.accepted" aria-label="Accept risk suggestion">
                <input class="input-field text-xs" [(ngModel)]="item.description" aria-label="Suggested risk description">
                <select class="input-field text-xs" [(ngModel)]="item.impact" aria-label="Suggested risk impact">
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                </select>
                <select class="input-field text-xs" [(ngModel)]="item.likelihood" aria-label="Suggested risk likelihood">
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                </select>
              </label>
            </section>

            <section class="card p-4">
              <h4 class="text-sm font-bold mb-3" style="color:var(--t-text-primary)">Milestones</h4>
              <label *ngFor="let item of suggestionSet.milestones"
                     class="grid grid-cols-[auto_1fr_120px] gap-3 items-center mb-2">
                <input type="checkbox" [(ngModel)]="item.accepted" aria-label="Accept milestone suggestion">
                <input class="input-field text-xs" [(ngModel)]="item.name" aria-label="Suggested milestone name">
                <select class="input-field text-xs" [(ngModel)]="item.priority" aria-label="Suggested milestone priority">
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                </select>
              </label>
            </section>
          </div>
        </div>

        <!-- NAVIGATION BUTTONS -->
        <div class="flex items-center justify-between mt-8 pt-5 border-t"
             style="border-color:var(--t-border)">
          <button *ngIf="formStep > 1" class="btn-secondary text-sm"
                  (click)="formStep = formStep - 1"
                  aria-label="Go to previous step">
            ← Back
          </button>
          <button *ngIf="formStep === 1" class="btn-ghost text-sm"
                  (click)="currentPath = 'chooser'"
                  aria-label="Return to path chooser">
            ← Change method
          </button>

          <div class="flex items-center gap-3">
            <button *ngIf="formStep < 3" class="btn-primary text-sm"
                    (click)="formStep = formStep + 1"
                    [disabled]="formStep === 1 && !form.name.trim()"
                    aria-label="Go to next step">
              Next →
            </button>
            <button *ngIf="formStep === 3 && !editId" class="btn-primary text-sm"
                    (click)="generateSuggestions()"
                    [disabled]="submitting() || generating() || isCreationBlocked()"
                    aria-label="Generate initiative suggestions">
              <span *ngIf="!generating()">Generate Suggestions</span>
              <span *ngIf="generating()">Generating…</span>
            </button>
            <button *ngIf="formStep === 3 && editId" class="btn-primary text-sm"
                    (click)="submitForm()"
                    [disabled]="submitting()"
                    aria-label="Save initiative">
              <span *ngIf="!submitting()">Save Initiative</span>
              <span *ngIf="submitting()" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                </svg>
                Saving…
              </span>
            </button>
            <button *ngIf="formStep === 4" class="btn-primary text-sm"
                    (click)="submitForm()"
                    [disabled]="submitting() || isCreationBlocked()"
                    aria-label="Create initiative">
              <span *ngIf="!submitting()">Create Initiative</span>
              <span *ngIf="submitting()">Creating…</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Error display -->
      <div *ngIf="error()" class="mt-4 p-4 rounded-lg text-sm"
           style="background:rgba(239,68,68,0.08);color:var(--t-red);border:1px solid rgba(239,68,68,0.2)">
        {{ error() }}
      </div>
    </div>

    <!-- ═══════════════ EXCEL UPLOAD ═══════════════ -->
    <div *ngIf="currentPath === 'upload'" class="slide-up">
      <div *ngIf="!editId && isCreationBlocked()" class="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
        <p class="text-[10px] font-black uppercase tracking-widest text-amber-600">Tenant setup required</p>
        <p class="mt-2 text-sm font-bold text-[var(--t-text-primary)]">Upload is disabled until the tenant setup checklist is complete.</p>
        <p class="mt-1 text-sm leading-6 text-[var(--t-text-secondary)]">
          Configure business units, workstreams, financial engine definitions, stage gates, and gate criteria in Admin first.
        </p>
      </div>

      <h1 class="text-3xl font-bold tracking-tight mb-2"
          style="color:var(--t-text-primary)">
        Upload Initiative<span style="color:var(--t-accent)">.</span>
      </h1>
      <p class="mb-6" style="color:var(--t-text-secondary)">
        Upload a pre-filled Transmuter Excel template to create an initiative with all data.
      </p>

      <div class="card p-6">
        <div class="upload-zone"
             [class.dragover]="isDragOver"
             (dragover)="onDragOver($event)"
             (dragleave)="isDragOver = false"
             (drop)="onDrop($event)"
             (click)="fileInput.click()"
             role="button" tabindex="0"
             aria-label="Drop Excel file here or click to browse">
          <input #fileInput type="file" class="hidden"
                 accept=".xlsx,.xls"
                 (change)="onFileSelected($event)"
                 aria-hidden="true">
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
               style="background:var(--t-accent-soft)">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"
                 fill="none" stroke="var(--t-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>
              <line x1="12" x2="12" y1="3" y2="15"/>
            </svg>
          </div>
          <p class="font-medium mb-1" style="color:var(--t-text-primary)">
            Drop your Excel file here
          </p>
          <p class="text-sm" style="color:var(--t-text-secondary)">
            or <span style="color:var(--t-accent)" class="underline">browse files</span>
            — .xlsx format only
          </p>
        </div>

        <div *ngIf="uploadedFileName()" class="mt-4 p-3 rounded-lg flex items-center justify-between"
             style="background:var(--t-surface-raised);border:1px solid var(--t-border)">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center"
                 style="background:rgba(16,185,129,0.1)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="var(--t-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 6 9 17l-5-5"/>
              </svg>
            </div>
            <span class="text-sm font-medium" style="color:var(--t-text-primary)">{{ uploadedFileName() }}</span>
          </div>
          <button class="btn-ghost text-xs" (click)="clearUpload()" aria-label="Remove uploaded file">✕</button>
        </div>

        <div *ngIf="uploadPreview()" class="mt-4 rounded-xl border p-4"
             style="border-color:var(--t-border);background:var(--t-bg)">
          <p class="text-[10px] font-bold uppercase tracking-wider mb-2" style="color:var(--t-text-secondary)">Preview</p>
          <p class="text-sm font-bold" style="color:var(--t-text-primary)">{{ uploadPreview()?.name }}</p>
          <p class="text-xs mt-1" style="color:var(--t-text-secondary)">
            {{ uploadPreview()?.country || 'No country' }} · {{ uploadPreview()?.priority || 'medium' }} priority
          </p>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mt-3">
            <div *ngFor="let key of workbookCountKeys"
                 class="rounded-lg border px-3 py-2"
                 style="border-color:var(--t-border);background:var(--t-surface-raised)">
              <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">{{ key }}</p>
              <p class="text-sm font-bold" style="color:var(--t-text-primary)">{{ uploadPreview()?.counts?.[key] || 0 }}</p>
            </div>
          </div>
          <div *ngIf="uploadPreview()?.validation_errors?.length"
               class="mt-3 rounded-lg border p-3 text-xs"
               style="border-color:rgba(239,68,68,0.25);background:rgba(239,68,68,0.08);color:var(--t-red)">
            <p class="font-bold mb-1">Validation required</p>
            <p *ngFor="let item of uploadPreview()?.validation_errors">
              {{ item.sheet }}<span *ngIf="item.row"> row {{ item.row }}</span><span *ngIf="item.column"> {{ item.column }}</span>: {{ item.message }}
            </p>
          </div>
        </div>

        <div class="flex items-center justify-between mt-6 pt-5 border-t"
             style="border-color:var(--t-border)">
          <button class="btn-ghost text-sm" (click)="currentPath = 'chooser'"
                  aria-label="Return to path chooser">
            ← Change method
          </button>
          <button class="btn-primary text-sm"
                  [disabled]="!uploadedFileName() || submitting() || !!uploadPreview()?.validation_errors?.length || isCreationBlocked()"
                  (click)="submitUpload()"
                  aria-label="Upload and create initiative">
            <span *ngIf="!submitting()">Upload & Create</span>
            <span *ngIf="submitting()">Uploading…</span>
          </button>
        </div>
      </div>

      <div *ngIf="error()" class="mt-4 p-4 rounded-lg text-sm"
           style="background:rgba(239,68,68,0.08);color:var(--t-red);border:1px solid rgba(239,68,68,0.2)">
        {{ error() }}
      </div>
    </div>

  </div>
</div>
  `,
})
export class CreateInitiativeComponent {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  currentPath: CreationPath = 'chooser';
  formStep = 1;
  isDragOver = false;
  editId: string | null = null;

  readonly submitting = signal(false);
  readonly generating = signal(false);
  readonly error = signal<string | null>(null);
  readonly workstreams = signal<WorkstreamOption[]>([]);
  readonly businessUnits = signal<BusinessUnitOption[]>([]);
  readonly markets = signal<string[]>([]);
  readonly themes = signal<string[]>([]);
  readonly tags = signal<string[]>([]);
  readonly users = signal<UserOption[]>([]);
  readonly financialConfiguration = signal<FinancialConfiguration | null>(null);
  readonly financialEngineConfiguration = signal<any>({ definitions: [], scenarios: [], cost_categories: [], settings: {} });
  readonly stageGateDefinitions = signal<any[]>([]);
  readonly gateCriteria = signal<any[]>([]);
  readonly financialSelectionsLocked = signal(false);
  readonly financialSelectionsLockReason = signal<string | null>(null);
  readonly baselineLocked = signal(false);
  readonly baselineLockReason = signal<string | null>(null);
  readonly setupStatus = signal<any>({ complete: false, completed: 0, total: 0, checks: [] });
  readonly setupStatusLoaded = signal(false);
  readonly selectedMetricKeys = signal<string[]>([
    'revenue_uplift_base',
    'revenue_uplift_high',
    'revenue_uplift_actual',
    'gm_uplift_base',
    'gm_uplift_high',
    'gm_uplift_actual',
  ]);
  readonly selectedCostCategoryKeys = signal<string[]>(['implementation', 'maintenance']);
  readonly uploadedFileName = signal<string | null>(null);
  readonly uploadPreview = signal<any | null>(null);
  readonly suggestions = signal<any | null>(null);
  readonly workbookCountKeys = ['financials', 'costs', 'kpis', 'risks', 'milestones'];
  private readonly defaultTags = ['automation', 'offshoring', 'commercial', 'other'];

  private uploadedFile: File | null = null;

  form = {
    name: '',
    business_unit_ids: [] as string[],
    workstream_id: '',
    owner_id: '',
    group_owner_id: '',
    type: '',
    impact_type: '',
    theme: '',
    country: '',
    tag: '',
    priority: 'medium',
    summary: '',
    context_problem: '',
    value_logic: '',
    dependencies_text: '',
    planned_start: '',
    planned_end: '',
    baseline_year: new Date().getFullYear(),
    baseline_values: {} as Record<string, string>,
  };

  constructor() {
    this.loadDropdownData();
    this.loadSetupStatus();
    this.editId = this.route.snapshot.paramMap.get('id');
    if (this.editId) {
      this.currentPath = 'form';
      this.loadForEdit(this.editId);
    }
  }

  stepLabel(): string {
    return this.formStep === 1 ? 'Basic Details'
         : this.formStep === 2 ? 'Description & Context'
         : this.formStep === 3 ? 'Ownership & Timeline'
         : 'Review Suggestions';
  }

  totalSteps(): number[] {
    return this.editId ? [1, 2, 3] : [1, 2, 3, 4];
  }

  /** Load workstreams and users for dropdowns */
  private loadDropdownData(): void {
    this.api.get<{ data: WorkstreamOption[] }>('/workstreams').subscribe({
      next: r => this.workstreams.set(r.data ?? []),
      error: () => {},  // graceful — dropdowns remain empty
    });
    this.api.get<{ data: BusinessUnitOption[] }>('/business-units').subscribe({
      next: r => this.businessUnits.set(r.data ?? []),
      error: () => {},
    });
    this.api.get<any>('/admin/settings').subscribe({
      next: r => {
        const strategicParameters = r.settings?.strategic_parameters || {};
        this.markets.set(this.normalizeConfigList(strategicParameters.markets));
        this.themes.set(this.normalizeConfigList(strategicParameters.themes));
        const configuredTags = this.normalizeConfigList(strategicParameters.tags);
        this.tags.set(configuredTags.length ? configuredTags : this.defaultTags);
      },
      error: () => {},
    });
    this.api.get<{ data: UserOption[] }>('/users').subscribe({
      next: r => this.users.set(r.data ?? []),
      error: () => {},
    });
    this.api.get<FinancialConfiguration>('/financial-configuration').subscribe({
      next: r => this.financialConfiguration.set(r),
      error: () => this.financialConfiguration.set(null),
    });
    this.api.get<any>('/financial-engine-configuration').subscribe({
      next: r => this.financialEngineConfiguration.set(r || { definitions: [], scenarios: [], cost_categories: [], settings: {} }),
      error: () => this.financialEngineConfiguration.set({ definitions: [], scenarios: [], cost_categories: [], settings: {} }),
    });
    this.api.get<any[]>('/governance/stage-gates').subscribe({
      next: r => this.stageGateDefinitions.set(Array.isArray(r) ? r : []),
      error: () => this.stageGateDefinitions.set([]),
    });
    this.api.get<any>('/admin/governance/gate-criteria').subscribe({
      next: r => this.gateCriteria.set(Array.isArray(r) ? r : (r.items || [])),
      error: () => this.gateCriteria.set([]),
    });
  }

  private loadSetupStatus(): void {
    if (this.auth.getRole() !== 'transformation_office') {
      this.setupStatusLoaded.set(true);
      return;
    }
    this.api.get<any>('/admin/setup-status').subscribe({
      next: status => {
        this.setupStatus.set(status || { complete: false, completed: 0, total: 0, checks: [] });
        this.setupStatusLoaded.set(true);
      },
      error: () => {
        this.setupStatusLoaded.set(true);
      },
    });
  }

  private loadForEdit(id: string): void {
    this.api.get<any>(`/initiatives/${id}`).subscribe({
      next: item => {
        this.form = {
          name: item.name ?? '',
          business_unit_ids: item.business_unit_ids ?? [],
          workstream_id: item.workstream_id ?? '',
          owner_id: item.owner_id ?? '',
          group_owner_id: item.group_owner_id ?? '',
          type: item.type ?? '',
          impact_type: item.impact_type ?? '',
          theme: item.theme ?? '',
          country: item.country ?? '',
          tag: item.tag ?? '',
          priority: item.priority ?? 'medium',
          summary: item.summary ?? '',
          context_problem: item.context_problem ?? '',
          value_logic: item.value_logic ?? '',
          dependencies_text: item.dependencies_text ?? '',
          planned_start: item.planned_start ?? '',
          planned_end: item.planned_end ?? '',
          baseline_year: new Date().getFullYear(),
          baseline_values: {},
        };
      },
      error: err => this.error.set(this.errorText(err, 'Failed to load initiative for editing.')),
    });
    this.api.get<any>(`/initiatives/${id}/financials/selections`).subscribe({
      next: response => {
        const selected = response?.selected || {};
        this.financialSelectionsLocked.set(Boolean(response?.locked));
        this.financialSelectionsLockReason.set(response?.lock_reason || null);
        if (Array.isArray(selected.metric_keys) && selected.metric_keys.length) {
          this.selectedMetricKeys.set(selected.metric_keys);
        }
        if (Array.isArray(selected.cost_category_keys) && selected.cost_category_keys.length) {
          this.selectedCostCategoryKeys.set(selected.cost_category_keys);
        }
      },
      error: () => {},
    });
    this.api.get<any>(`/initiatives/${id}/financials/baseline`).subscribe({
      next: response => {
        this.baselineLocked.set(Boolean(response?.locked));
        this.baselineLockReason.set(response?.lock_reason || null);
        if (response?.baseline_year) this.form.baseline_year = Number(response.baseline_year);
        const values: Record<string, string> = {};
        for (const row of response?.values || []) {
          values[row.metric_definition_id] = row.value;
        }
        this.form.baseline_values = values;
      },
      error: () => {},
    });
  }

  private validateForm(): boolean {
    if (this.isCreationBlocked() && !this.editId) {
      this.error.set('Complete tenant setup in Admin before creating a new initiative.');
      return false;
    }
    if (!this.form.name.trim()) {
      this.error.set('Initiative name is required.');
      return false;
    }
    if (this.form.planned_start && this.form.planned_end && this.form.planned_start > this.form.planned_end) {
      this.error.set('Planned completion date must be on or after the planned start date.');
      return false;
    }
    this.error.set(null);
    return true;
  }

  private buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = { name: this.form.name.trim() };
    if (this.editId || this.form.workstream_id) payload['workstream_id'] = this.form.workstream_id || null;
    if (this.editId || this.form.business_unit_ids.length) payload['business_unit_ids'] = this.form.business_unit_ids;
    if (this.form.owner_id) payload['owner_id'] = this.form.owner_id;
    if (this.form.group_owner_id) payload['group_owner_id'] = this.form.group_owner_id;
    if (this.form.type) payload['type'] = this.form.type;
    if (this.form.impact_type) payload['impact_type'] = this.form.impact_type;
    if (this.editId || this.form.theme) payload['theme'] = this.form.theme || null;
    if (this.editId || this.form.country) payload['country'] = this.form.country || null;
    if (this.editId || this.form.tag) payload['tag'] = this.form.tag || null;
    if (this.form.priority) payload['priority'] = this.form.priority;
    if (this.editId || this.form.summary) payload['summary'] = this.form.summary || null;
    if (this.editId || this.form.context_problem) payload['context_problem'] = this.form.context_problem || null;
    if (this.editId || this.form.value_logic) payload['value_logic'] = this.form.value_logic || null;
    if (this.editId || this.form.dependencies_text) payload['dependencies_text'] = this.form.dependencies_text || null;
    if (this.form.planned_start) payload['planned_start'] = this.form.planned_start;
    if (this.form.planned_end) payload['planned_end'] = this.form.planned_end;
    return payload;
  }

  marketOptions(): string[] {
    return this.withCurrentOption(this.markets(), this.form.country);
  }

  themeOptions(): string[] {
    return this.withCurrentOption(this.themes(), this.form.theme);
  }

  tagOptions(): string[] {
    return this.withCurrentOption(this.tags(), this.form.tag);
  }

  financialMetricOptions(): FinancialConfigItem[] {
    return this.sortedFinancialItems('metric');
  }

  baselineMetricOptions(): any[] {
    const definitions = this.financialEngineConfiguration()?.definitions || [];
    const eligibleKeys = this.baselineMetricKeys(definitions);
    return definitions
      .filter((metric: any) =>
        metric?.is_active !== false
        && metric?.aggregation !== 'formula'
        && eligibleKeys.has(String(metric?.key || ''))
      )
      .sort((a: any, b: any) =>
        Number(a.display_order || 0) - Number(b.display_order || 0)
        || String(a.label || '').localeCompare(String(b.label || '')),
      );
  }

  private baselineMetricKeys(definitions: any[]): Set<string> {
    const activeNonFormula = new Set(
      definitions
        .filter((metric: any) => metric?.is_active !== false && metric?.aggregation !== 'formula')
        .map((metric: any) => String(metric?.key || ''))
        .filter(Boolean),
    );
    const keys = new Set<string>();
    for (const metric of definitions) {
      const key = String(metric?.key || '');
      if (activeNonFormula.has(key) && String(metric?.group_key || '') === 'baseline') {
        keys.add(key);
      }
      if (metric?.aggregation !== 'formula' || metric?.is_active === false) continue;
      const identifiers = new Set<string>(Array.isArray(metric?.formula_inputs) ? metric.formula_inputs.map(String) : []);
      String(metric?.formula || '').replace(/\b[A-Za-z_][A-Za-z0-9_]*\b/g, identifier => {
        identifiers.add(identifier);
        return identifier;
      });
      identifiers.forEach(identifier => {
        if (!identifier.startsWith('baseline_')) return;
        const baselineKey = identifier.replace(/^baseline_/, '');
        if (activeNonFormula.has(baselineKey)) keys.add(baselineKey);
      });
    }
    return keys;
  }

  baselineMetricValue(metricDefinitionId: string): string {
    return this.form.baseline_values[metricDefinitionId] || '';
  }

  setBaselineMetricValue(metricDefinitionId: string, value: string | number): void {
    this.form.baseline_values = {
      ...this.form.baseline_values,
      [metricDefinitionId]: String(value ?? ''),
    };
  }

  costCategoryOptions(): FinancialConfigItem[] {
    return this.sortedFinancialItems('cost_category');
  }

  isMetricSelected(item: FinancialConfigItem): boolean {
    return this.selectedMetricKeys().includes(this.financialMetricKey(item));
  }

  isCostCategorySelected(item: FinancialConfigItem): boolean {
    return this.selectedCostCategoryKeys().includes(item.key);
  }

  toggleMetric(item: FinancialConfigItem, checked: boolean): void {
    this.toggleSelection(this.selectedMetricKeys, this.financialMetricKey(item), checked);
  }

  toggleCostCategory(item: FinancialConfigItem, checked: boolean): void {
    this.toggleSelection(this.selectedCostCategoryKeys, item.key, checked);
  }

  isBusinessUnitSelected(businessUnitId: string): boolean {
    return this.form.business_unit_ids.includes(businessUnitId);
  }

  toggleBusinessUnit(businessUnitId: string, checked: boolean): void {
    const current = new Set(this.form.business_unit_ids);
    if (checked) current.add(businessUnitId);
    else current.delete(businessUnitId);
    this.form.business_unit_ids = Array.from(current);
  }

  private normalizeConfigList(values: unknown): string[] {
    if (!Array.isArray(values)) return [];
    return [...new Set(values.map(value => String(value).trim()).filter(Boolean))];
  }

  private withCurrentOption(options: string[], currentValue: string): string[] {
    const current = currentValue.trim();
    return this.normalizeConfigList(current ? [...options, current] : options);
  }

  private sortedFinancialItems(type: 'metric' | 'cost_category'): FinancialConfigItem[] {
    const config = this.financialConfiguration();
    if (!config) return [];
    const groups = new Map(config.groups.map(group => [group.key, group]));
    return config.items
      .filter(item => item.item_type === type && item.is_active)
      .sort((a, b) => {
        const groupA = groups.get(a.group_key || '')?.display_order || 0;
        const groupB = groups.get(b.group_key || '')?.display_order || 0;
        return groupA - groupB || a.display_order - b.display_order || a.label.localeCompare(b.label);
      });
  }

  private financialMetricKey(item: FinancialConfigItem): string {
    return item.system_metric_key || item.key;
  }

  private toggleSelection(target: WritableSignal<string[]>, key: string, checked: boolean): void {
    const current = new Set(target());
    if (checked) current.add(key);
    else current.delete(key);
    target.set(Array.from(current));
  }

  labelize(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  generateSuggestions(): void {
    if (this.isCreationBlocked() && !this.editId) {
      this.error.set('Complete tenant setup in Admin before generating new initiative suggestions.');
      return;
    }
    if (!this.validateForm()) return;

    this.generating.set(true);
    this.error.set(null);
    this.api.post<any>('/initiatives/intake/suggestions', {
      initiative: this.buildPayload(),
      conversation: [],
    }).subscribe({
      next: result => {
        this.generating.set(false);
        this.formStep = 4;
        this.suggestions.set(result);
      },
      error: err => {
        this.generating.set(false);
        this.error.set(this.errorText(err, 'Failed to generate initiative suggestions.'));
      },
    });
  }

  /** Submit the guided form or edit form */
  submitForm(): void {
    if (!this.validateForm()) return;

    this.submitting.set(true);
    this.error.set(null);

    const payload = this.buildPayload();
    const request = this.editId
      ? this.api.put<{ id: string }>(`/initiatives/${this.editId}`, payload)
      : this.api.post<{ id: string }>('/initiatives/intake/create', {
          initiative: payload,
          suggestions: this.suggestions(),
        });

    request.subscribe({
      next: result => {
        const initiativeId = result.id || this.editId;
        if (!initiativeId) {
          this.submitting.set(false);
          this.router.navigate(['/initiatives/pipeline']);
          return;
        }
        this.saveFinancialSelections(initiativeId);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(this.errorText(err, this.editId
          ? 'Failed to save initiative. Please try again.'
          : 'Failed to create initiative. Please try again.'));
      },
    });
  }

  private saveFinancialSelections(initiativeId: string): void {
    this.api.put(`/initiatives/${initiativeId}/financials/selections`, {
      metric_keys: this.selectedMetricKeys(),
      cost_category_keys: this.selectedCostCategoryKeys(),
    }).subscribe({
      next: () => this.saveAnnualBaseline(initiativeId),
      error: err => {
        this.submitting.set(false);
        this.error.set(this.errorText(err, 'Initiative saved, but financial selections could not be updated.'));
      },
    });
  }

  private saveAnnualBaseline(initiativeId: string): void {
    const baselineYear = Number(this.form.baseline_year);
    const values = Object.entries(this.form.baseline_values)
      .map(([metric_definition_id, raw]) => ({
        metric_definition_id,
        baseline_year: baselineYear,
        value: String(raw ?? '').trim(),
      }))
      .filter(row => row.value !== '');
    if (!values.length || this.baselineLocked()) {
      this.submitting.set(false);
      this.router.navigate(['/initiatives', initiativeId]);
      return;
    }
    this.api.put(`/initiatives/${initiativeId}/financials/baseline`, {
      baseline_year: baselineYear,
      values,
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.router.navigate(['/initiatives', initiativeId]);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(this.errorText(err, 'Initiative saved, but annual baseline values could not be updated.'));
      },
    });
  }

  /** File upload handlers */
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const file = event.dataTransfer?.files?.[0];
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      this.uploadedFile = file;
      this.uploadedFileName.set(file.name);
      this.previewUpload(file);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.uploadedFile = file;
      this.uploadedFileName.set(file.name);
      this.previewUpload(file);
    }
  }

  clearUpload(): void {
    this.uploadedFile = null;
    this.uploadedFileName.set(null);
    this.uploadPreview.set(null);
  }

  downloadTemplate(event?: Event): void {
    event?.stopPropagation();
    this.api.getBlob('/initiatives/template').subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'transmuter-initiative-template.xlsx';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.error.set('Failed to download initiative template.'),
    });
  }

  previewUpload(file: File): void {
    const body = new FormData();
    body.append('file', file);
    this.api.postForm<any>('/initiatives/import/preview', body).subscribe({
      next: preview => {
        this.uploadPreview.set(preview);
        this.error.set(preview.validation_errors?.length ? 'Fix workbook validation errors before importing.' : null);
      },
      error: err => {
        this.uploadPreview.set(null);
        this.error.set(this.errorText(err, 'Failed to preview template. Please check the file format.'));
      },
    });
  }

  submitUpload(): void {
    if (!this.uploadedFile) return;
    if (this.isCreationBlocked() && !this.editId) {
      this.error.set('Complete tenant setup in Admin before uploading a new initiative.');
      return;
    }

    this.submitting.set(true);
    this.error.set(null);

    const formData = new FormData();
    formData.append('file', this.uploadedFile);

    this.api.postForm<{ id: string }>('/initiatives/import', formData).subscribe({
      next: result => {
        this.submitting.set(false);
        this.router.navigate(['/initiatives', result.id]);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(this.errorText(err, 'Failed to parse template. Please check the file format.'));
      },
    });
  }

  private errorText(err: any, fallback: string): string {
    const detail = err?.error?.detail;
    if (Array.isArray(detail)) {
      return detail
        .map(item => `${item.sheet ?? 'Workbook'}${item.row ? ` row ${item.row}` : ''}${item.column ? ` ${item.column}` : ''}: ${item.message ?? 'Invalid value'}`)
        .join('\n');
    }
    return detail ?? fallback;
  }

  isCreationBlocked(): boolean {
    if (this.editId) return false;
    const localReady = this.hasLocalSetupReady();
    if (this.auth.getRole() === 'transformation_office' && this.setupStatusLoaded()) {
      return !Boolean(this.setupStatus()?.complete) || !localReady;
    }
    return !localReady;
  }

  private hasLocalSetupReady(): boolean {
    return Boolean(
      this.businessUnits().length &&
      this.workstreams().length &&
      this.financialEngineConfiguration()?.definitions?.length &&
      this.financialEngineConfiguration()?.scenarios?.length &&
      this.financialEngineConfiguration()?.cost_categories?.length &&
      this.stageGateDefinitions().length &&
      this.gateCriteria().length
    );
  }
}
