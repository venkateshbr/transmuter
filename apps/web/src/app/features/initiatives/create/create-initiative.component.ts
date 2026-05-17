import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface WorkstreamOption {
  id: string;
  name: string;
  business_unit_id: string | null;
}

interface BusinessUnitOption {
  id: string;
  name: string;
}

interface UserOption {
  id: string;
  display_name: string;
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

    .confidence-badge {
      display: inline-flex;
      align-items: center;
      height: 18px;
      border: 1px solid var(--t-border);
      padding: 0 6px;
      font-size: 0.625rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      background: var(--t-surface-raised);
      color: var(--t-text-secondary);
    }
    .confidence-high { border-color: rgba(16,185,129,0.35); color: var(--t-green); }
    .confidence-medium { border-color: rgba(59,130,246,0.35); color: var(--t-accent); }
    .confidence-low { border-color: rgba(245,158,11,0.35); color: var(--t-amber); }
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
        <div class="mb-5 rounded-xl border p-4 flex items-start justify-between gap-4"
             style="background:var(--t-accent-soft);border-color:var(--t-border)">
          <div class="flex items-start gap-3">
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
          <button *ngIf="!editId"
                  class="btn-secondary text-xs whitespace-nowrap"
                  (click)="generateSuggestions()"
                  [disabled]="generating() || submitting() || !form.name.trim()"
                  aria-label="Start AI-assisted initiative review">
            <span *ngIf="!generating()">AI Assist</span>
            <span *ngIf="generating()">Working...</span>
          </button>
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
              <select id="init-workstream" class="input-field" [(ngModel)]="form.workstream_id" (ngModelChange)="onWorkstreamChange($event)">
                <option value="">Select workstream</option>
                <option *ngFor="let ws of filteredWorkstreams()" [value]="ws.id">{{ ws.name }}</option>
              </select>
            </div>
            <div>
              <label for="init-business-unit" class="field-label">Business Unit</label>
              <select id="init-business-unit" class="input-field" [(ngModel)]="form.business_unit_id" (ngModelChange)="onBusinessUnitChange($event)">
                <option value="">Select business unit</option>
                <option *ngFor="let bu of businessUnits()" [value]="bu.id">{{ bu.name }}</option>
              </select>
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
        </div>

        <!-- STEP 4: HITL Suggestions -->
        <div *ngIf="formStep === 4" class="space-y-5 animate-in">
          <div class="rounded-xl border p-4" style="border-color:var(--t-border);background:var(--t-bg)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">HITL Review</p>
                <h3 class="text-lg font-bold" style="color:var(--t-text-primary)">Transmuter extracted the following — review and edit before saving</h3>
                <p class="text-sm mt-1" style="color:var(--t-text-secondary)">
                  Field confidence is shown beside extracted fields. Accept, reject, or edit KPIs and risks before committing to the database.
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
              <h4 class="text-sm font-bold mb-3" style="color:var(--t-text-primary)">Extracted Initiative Fields</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-name" class="field-label mb-0">Name</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('name')">{{ confidenceFor('name') }}</span>
                  </div>
                  <input id="review-name" class="input-field text-xs" [(ngModel)]="form.name" aria-label="Review extracted initiative name">
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-type" class="field-label mb-0">Type</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('type')">{{ confidenceFor('type') }}</span>
                  </div>
                  <select id="review-type" class="input-field text-xs" [(ngModel)]="form.type" aria-label="Review extracted initiative type">
                    <option value="">Select type</option>
                    <option value="revenue_growth">Revenue Growth</option>
                    <option value="cost_reduction">Cost Reduction</option>
                    <option value="cost_avoidance">Cost Avoidance</option>
                    <option value="compliance">Compliance</option>
                    <option value="capability_building">Capability Building</option>
                  </select>
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-workstream" class="field-label mb-0">Workstream</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('workstream')">{{ confidenceFor('workstream') }}</span>
                  </div>
                  <select id="review-workstream" class="input-field text-xs" [(ngModel)]="form.workstream_id" (ngModelChange)="onWorkstreamChange($event)" aria-label="Review extracted workstream">
                    <option value="">Select workstream</option>
                    <option *ngFor="let ws of filteredWorkstreams()" [value]="ws.id">{{ ws.name }}</option>
                  </select>
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-priority" class="field-label mb-0">Priority</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('priority')">{{ confidenceFor('priority') }}</span>
                  </div>
                  <select id="review-priority" class="input-field text-xs" [(ngModel)]="form.priority" aria-label="Review extracted priority">
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-country" class="field-label mb-0">Market</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('country')">{{ confidenceFor('country') }}</span>
                  </div>
                  <input id="review-country" class="input-field text-xs" [(ngModel)]="form.country" aria-label="Review extracted market">
                </div>
                <div class="md:col-span-2">
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-summary" class="field-label mb-0">Summary</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('summary')">{{ confidenceFor('summary') }}</span>
                  </div>
                  <textarea id="review-summary" class="input-field text-xs" rows="2" [(ngModel)]="form.summary" aria-label="Review extracted summary"></textarea>
                </div>
                <div class="md:col-span-2">
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-value-logic" class="field-label mb-0">Value Logic</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('value_logic')">{{ confidenceFor('value_logic') }}</span>
                  </div>
                  <textarea id="review-value-logic" class="input-field text-xs" rows="2" [(ngModel)]="form.value_logic" aria-label="Review extracted value logic"></textarea>
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-planned-end" class="field-label mb-0">Planned Completion</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('planned_end')">{{ confidenceFor('planned_end') }}</span>
                  </div>
                  <input id="review-planned-end" type="date" class="input-field text-xs" [(ngModel)]="form.planned_end" aria-label="Review extracted completion date">
                </div>
                <div>
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <label for="review-dependencies" class="field-label mb-0">Dependencies</label>
                    <span class="confidence-badge" [ngClass]="'confidence-' + confidenceFor('dependencies')">{{ confidenceFor('dependencies') }}</span>
                  </div>
                  <input id="review-dependencies" class="input-field text-xs" [(ngModel)]="form.dependencies_text" aria-label="Review extracted dependencies">
                </div>
              </div>
            </section>

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
                    [disabled]="submitting() || generating()"
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
                    [disabled]="submitting()"
                    aria-label="Create initiative">
              <span *ngIf="!submitting()">Save Initiative</span>
              <span *ngIf="submitting()">Creating…</span>
            </button>
            <button *ngIf="formStep === 4" class="btn-secondary text-sm"
                    (click)="cancelWorkflow()"
                    [disabled]="submitting()"
                    aria-label="Cancel initiative intake review">
              Cancel
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
                  [disabled]="!uploadedFileName() || submitting() || !!uploadPreview()?.validation_errors?.length"
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
  readonly uploadedFileName = signal<string | null>(null);
  readonly uploadPreview = signal<any | null>(null);
  readonly suggestions = signal<any | null>(null);
  readonly workflowRunId = signal<string | null>(null);
  readonly fieldConfidence = signal<Record<string, 'high' | 'medium' | 'low'>>({});
  readonly workbookCountKeys = ['financials', 'costs', 'kpis', 'risks', 'milestones'];
  private readonly defaultTags = ['automation', 'offshoring', 'commercial', 'other'];

  private uploadedFile: File | null = null;

  form = {
    name: '',
    business_unit_id: '',
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
    value_logic: '',
    dependencies_text: '',
    planned_start: '',
    planned_end: '',
  };

  constructor() {
    this.loadDropdownData();
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
  }

  private loadForEdit(id: string): void {
    this.api.get<any>(`/initiatives/${id}`).subscribe({
      next: item => {
        this.form = {
          name: item.name ?? '',
          business_unit_id: item.business_unit_id ?? '',
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
          value_logic: item.value_logic ?? '',
          dependencies_text: item.dependencies_text ?? '',
          planned_start: item.planned_start ?? '',
          planned_end: item.planned_end ?? '',
        };
      },
      error: err => this.error.set(this.errorText(err, 'Failed to load initiative for editing.')),
    });
  }

  private validateForm(): boolean {
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
    if (this.form.owner_id) payload['owner_id'] = this.form.owner_id;
    if (this.form.group_owner_id) payload['group_owner_id'] = this.form.group_owner_id;
    if (this.form.type) payload['type'] = this.form.type;
    if (this.form.impact_type) payload['impact_type'] = this.form.impact_type;
    if (this.editId || this.form.theme) payload['theme'] = this.form.theme || null;
    if (this.editId || this.form.country) payload['country'] = this.form.country || null;
    if (this.editId || this.form.tag) payload['tag'] = this.form.tag || null;
    if (this.form.priority) payload['priority'] = this.form.priority;
    if (this.form.summary) payload['summary'] = this.form.summary;
    if (this.form.value_logic) payload['value_logic'] = this.form.value_logic;
    if (this.form.dependencies_text) payload['dependencies_text'] = this.form.dependencies_text;
    if (this.form.planned_start) payload['planned_start'] = this.form.planned_start;
    if (this.form.planned_end) payload['planned_end'] = this.form.planned_end;
    return payload;
  }

  filteredWorkstreams(): WorkstreamOption[] {
    const businessUnitId = this.form.business_unit_id;
    if (!businessUnitId) return this.workstreams();
    return this.workstreams().filter(ws => ws.business_unit_id === businessUnitId);
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

  onBusinessUnitChange(businessUnitId: string): void {
    this.form.business_unit_id = businessUnitId;
    if (!businessUnitId) return;
    const selectedWorkstream = this.workstreams().find(ws => ws.id === this.form.workstream_id);
    if (selectedWorkstream && selectedWorkstream.business_unit_id !== businessUnitId) {
      this.form.workstream_id = '';
    }
  }

  onWorkstreamChange(workstreamId: string): void {
    this.form.workstream_id = workstreamId;
    const selectedWorkstream = this.workstreams().find(ws => ws.id === workstreamId);
    if (selectedWorkstream?.business_unit_id) {
      this.form.business_unit_id = selectedWorkstream.business_unit_id;
    }
  }

  private normalizeConfigList(values: unknown): string[] {
    if (!Array.isArray(values)) return [];
    return [...new Set(values.map(value => String(value).trim()).filter(Boolean))];
  }

  private withCurrentOption(options: string[], currentValue: string): string[] {
    const current = currentValue.trim();
    return this.normalizeConfigList(current ? [...options, current] : options);
  }

  labelize(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  generateSuggestions(): void {
    if (!this.validateForm()) return;

    this.generating.set(true);
    this.error.set(null);
    this.workflowRunId.set(null);
    this.api.post<any>('/workflows/initiative-intake', {
      raw_text: this.buildIntakeText(),
    }).subscribe({
      next: result => {
        this.workflowRunId.set(result.workflow_run_id);
        this.loadWorkflowReview(result.workflow_run_id);
      },
      error: err => {
        this.generating.set(false);
        this.fallbackToBlankReview(this.errorText(err, 'AI extraction failed. Continue from the blank review form.'));
      },
    });
  }

  private loadWorkflowReview(workflowRunId: string): void {
    this.api.get<any>(`/workflows/${workflowRunId}/review`).subscribe({
      next: review => {
        this.applyExtractedDraft(review.extracted_draft ?? {});
        this.fieldConfidence.set(review.field_confidence ?? {});
        this.api.post<any>('/initiatives/intake/suggestions', {
          initiative: this.buildPayload(),
          conversation: [],
        }).subscribe({
          next: generated => {
            this.generating.set(false);
            this.suggestions.set({
              ...generated,
              trace_id: `workflow-${workflowRunId}`,
              agent_status: 'deterministic_fallback',
              kpis: this.mergeSuggestions(review.kpi_suggestions, generated.kpis, 'name'),
              risks: this.mergeSuggestions(review.risk_suggestions, generated.risks, 'description'),
            });
            this.formStep = 4;
          },
          error: () => {
            this.generating.set(false);
            this.suggestions.set({
              trace_id: `workflow-${workflowRunId}`,
              agent_status: 'deterministic_fallback',
              financial_entries: [],
              cost_lines: [],
              kpis: review.kpi_suggestions ?? [],
              risks: review.risk_suggestions ?? [],
              milestones: [],
            });
            this.formStep = 4;
          },
        });
      },
      error: err => {
        this.generating.set(false);
        this.workflowRunId.set(null);
        this.fallbackToBlankReview(this.errorText(err, 'AI extraction failed. Continue from the blank review form.'));
      },
    });
  }

  /** Submit the guided form or edit form */
  submitForm(): void {
    if (!this.validateForm()) return;

    this.submitting.set(true);
    this.error.set(null);

    const payload = this.buildPayload();
    const runId = this.workflowRunId();
    const request: any = this.editId
      ? this.api.put<{ id: string }>(`/initiatives/${this.editId}`, payload)
      : runId
        ? this.api.post<{ initiative: { id: string } }>(`/workflows/${runId}/approve`, {
            initiative: payload,
            suggestions: this.suggestions(),
          })
        : this.api.post<{ id: string }>('/initiatives/intake/create', {
            initiative: payload,
            suggestions: this.suggestions(),
          });

    request.subscribe({
      next: (result: any) => {
        this.submitting.set(false);
        const initiativeId = 'initiative' in result ? result.initiative.id : result.id;
        this.router.navigate(['/initiatives', initiativeId]);
      },
      error: (err: any) => {
        this.submitting.set(false);
        this.error.set(this.errorText(err, this.editId
          ? 'Failed to save initiative. Please try again.'
          : 'Failed to create initiative. Please try again.'));
      },
    });
  }

  cancelWorkflow(): void {
    const runId = this.workflowRunId();
    if (runId) {
      this.api.post<any>(`/workflows/${runId}/reject`, { reason: 'Cancelled from review panel.' }).subscribe({
        next: () => this.resetReview(),
        error: () => this.resetReview(),
      });
      return;
    }
    this.resetReview();
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

  confidenceFor(field: string): 'high' | 'medium' | 'low' {
    return this.fieldConfidence()[field] ?? 'low';
  }

  private buildIntakeText(): string {
    return [
      `Name: ${this.form.name}`,
      `Type: ${this.form.type}`,
      `Priority: ${this.form.priority}`,
      `Market: ${this.form.country}`,
      `Theme: ${this.form.theme}`,
      `Value logic: ${this.form.value_logic}`,
      `Summary: ${this.form.summary}`,
      `Dependencies: ${this.form.dependencies_text}`,
      `Planned end: ${this.form.planned_end}`,
    ].filter(line => !line.endsWith(': ')).join('\n');
  }

  private applyExtractedDraft(draft: Record<string, string | null>): void {
    if (draft['name'] && !this.form.name) this.form.name = draft['name'];
    if (draft['type'] && !this.form.type) this.form.type = draft['type'];
    if (draft['priority'] && !this.form.priority) this.form.priority = draft['priority'];
    if (draft['workstream'] && !this.form.workstream_id) {
      const normalized = draft['workstream'].toLowerCase();
      const match = this.workstreams().find(ws => ws.name.toLowerCase() === normalized);
      if (match) this.onWorkstreamChange(match.id);
    }
    if (draft['country'] && !this.form.country) this.form.country = draft['country'];
    if (draft['summary'] && !this.form.summary) this.form.summary = draft['summary'];
    if (draft['value_logic'] && !this.form.value_logic) this.form.value_logic = draft['value_logic'];
    if (draft['planned_end'] && !this.form.planned_end) this.form.planned_end = draft['planned_end'];
    if (draft['dependencies'] && !this.form.dependencies_text) {
      this.form.dependencies_text = draft['dependencies'];
    }
  }

  private fallbackToBlankReview(message: string): void {
    this.error.set(message);
    this.fieldConfidence.set({});
    this.suggestions.set({
      trace_id: 'manual-fallback',
      agent_status: 'deterministic_fallback',
      financial_entries: [],
      cost_lines: [],
      kpis: [],
      risks: [],
      milestones: [],
    });
    this.formStep = 4;
  }

  private resetReview(): void {
    this.workflowRunId.set(null);
    this.fieldConfidence.set({});
    this.suggestions.set(null);
    this.formStep = 3;
  }

  private mergeSuggestions(primary: any[] | null | undefined, fallback: any[] | null | undefined, key: string): any[] {
    const merged = [...(primary ?? [])];
    const existing = new Set(merged.map(item => String(item?.[key] ?? '').toLowerCase()).filter(Boolean));
    for (const item of fallback ?? []) {
      const value = String(item?.[key] ?? '').toLowerCase();
      if (value && existing.has(value)) continue;
      merged.push(item);
      if (value) existing.add(value);
    }
    return merged;
  }
}
