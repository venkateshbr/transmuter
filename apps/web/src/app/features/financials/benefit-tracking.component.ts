import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import {
  BenefitLedgerRollupSummaryResponse,
  BenefitLedgerSummaryResponse,
  FinancialLedgerGranularity,
  InitiativeOption,
  delta,
  formatDateOnly,
  formatMoney,
  initiativeLabel,
  parseNumeric,
  selectDefaultInitiative,
} from './financials-view.models';

type BenefitScope = 'portfolio' | 'workstream' | 'initiative';
type BenefitTrackingTab = 'summary' | 'ledger' | 'import';

interface WorkstreamOption {
  id: string;
  name: string;
}

interface BenefitLedgerEntry {
  id: string;
  initiative_id: string;
  period_granularity: FinancialLedgerGranularity;
  period_start: string;
  period_end: string;
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
  description?: string | null;
}

interface BenefitLedgerForm {
  id?: string;
  initiative_id: string;
  period_granularity: FinancialLedgerGranularity;
  period_start: string;
  period_end: string;
  actual_amount: string;
  description: string;
}

interface BenefitLedgerImportResult {
  created: number;
  updated: number;
  errors: Array<{ row: number; initiative_code?: string | null; message: string }>;
}

@Component({
  selector: 'app-benefit-tracking',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financials / Benefits Tracking</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">
            Locked Baseline Realization<span class="text-[var(--t-blue-light)]">.</span>
          </h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Portfolio and workstream rollups compare realized benefit ledger values against the locked bankable plan baseline.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <select
            class="input-field min-w-44 py-2 text-xs"
            [ngModel]="scope()"
            (ngModelChange)="setScope($event)"
            aria-label="Select benefit tracking scope">
            <option value="portfolio">Portfolio</option>
            <option value="workstream">Workstream</option>
            <option value="initiative">Initiative</option>
          </select>

          @if (scope() === 'workstream') {
            <select
              class="input-field min-w-64 py-2 text-xs"
              [ngModel]="selectedWorkstreamId()"
              (ngModelChange)="setSelectedWorkstream($event)"
              aria-label="Select workstream for benefit tracking">
              @for (workstream of workstreams(); track workstream.id) {
                <option [value]="workstream.id">{{ workstream.name }}</option>
              }
            </select>
          }

          @if (scope() === 'initiative') {
            <select
              class="input-field min-w-72 py-2 text-xs"
              [ngModel]="selectedInitiativeId()"
              (ngModelChange)="setSelectedInitiative($event)"
              aria-label="Select initiative for benefit tracking">
              @for (initiative of initiatives(); track initiative.id) {
                <option [value]="initiative.id">{{ initiativeLabel(initiative) }}</option>
              }
            </select>
            <a
              [routerLink]="['/initiatives', selectedInitiativeId(), 'financial-scope']"
              class="btn-secondary text-[10px]"
              [attr.aria-label]="'Open editable scope for ' + selectedInitiativeLabel()">
              Editable scope
            </a>
          }
        </div>
      </header>

      @if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      @if (success()) {
        <div class="border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-600">
          {{ success() }}
        </div>
      }

      <nav class="flex flex-wrap gap-2 border-b border-[var(--t-border)] pb-3" aria-label="Benefit tracking views">
        @for (tab of tabs; track tab.id) {
          <button
            type="button"
            class="border px-4 py-2 text-[10px] font-black uppercase tracking-widest"
            [class.border-[var(--t-primary)]]="activeTab() === tab.id"
            [class.bg-[var(--t-primary)]]="activeTab() === tab.id"
            [class.text-white]="activeTab() === tab.id"
            [class.border-[var(--t-border)]]="activeTab() !== tab.id"
            [class.text-[var(--t-text-secondary)]]="activeTab() !== tab.id"
            [attr.aria-pressed]="activeTab() === tab.id"
            (click)="setActiveTab(tab.id)">
            {{ tab.label }}
          </button>
        }
      </nav>

      @if (activeTab() === 'summary') {
      <section class="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <div class="card p-5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ scopeLabel() }}</p>
              <h2 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ summary().scope_name }}</h2>
              <p class="mt-2 text-sm font-bold text-[var(--t-text-secondary)]">
                {{ summary().initiatives.length }} initiatives / {{ summary().workstreams.length }} workstreams
              </p>
            </div>

            <div class="inline-flex border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-1" aria-label="Benefit granularity">
              @for (option of granularities; track option.id) {
                <button
                  type="button"
                  class="px-3 py-2 text-[10px] font-black uppercase tracking-widest"
                  [class.bg-[var(--t-primary)]]="granularity() === option.id"
                  [class.text-white]="granularity() === option.id"
                  [class.text-[var(--t-text-secondary)]]="granularity() !== option.id"
                  [attr.aria-pressed]="granularity() === option.id"
                  (click)="setGranularity(option.id)">
                  {{ option.label }}
                </button>
              }
            </div>
          </div>

          <div class="mt-6 grid gap-4 md:grid-cols-4">
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked baseline</p>
              <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().bankable_plan_amount) }}</p>
              <p class="mt-2 text-xs font-bold text-[var(--t-text-secondary)]">Net run-rate from bankable plans</p>
            </div>
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Realized</p>
              <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().actual_amount) }}</p>
              <p class="mt-2 text-xs font-bold text-[var(--t-text-secondary)]">Benefit ledger actuals</p>
            </div>
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Variance</p>
              <p class="mt-2 text-2xl font-black" [class.text-emerald-600]="delta(summary().actual_amount, summary().bankable_plan_amount) >= 0" [class.text-red-500]="delta(summary().actual_amount, summary().bankable_plan_amount) < 0">
                {{ formatMoney(summary().variance) }}
              </p>
              <p class="mt-2 text-xs font-bold text-[var(--t-text-secondary)]">Actual minus locked baseline</p>
            </div>
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Periods</p>
              <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ summary().periods.length }}</p>
              <p class="mt-2 text-xs font-bold text-[var(--t-text-secondary)]">{{ granularityLabel() }} realization rows</p>
            </div>
          </div>
        </div>

        <aside class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Baseline rule</p>
          <p class="mt-2 text-lg font-black text-[var(--t-text-primary)]">Locked plan is the comparator</p>
          <p class="mt-2 text-sm leading-6 text-[var(--t-text-secondary)]">
            Where ledger rows exist, the period plan is used. Where they do not, the latest locked bankable plan snapshot still contributes to the baseline total.
          </p>
        </aside>
      </section>

      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
          <div>
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Workstream rollup</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Locked baseline vs realized benefits</h2>
          </div>
          <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
            {{ summary().workstreams.length }} rows
          </span>
        </div>
        <div class="grid gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div class="min-h-72 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
            <div class="relative h-64 border-l border-b border-[var(--t-border)]">
              @for (row of summary().workstreams; track row.workstream_id || row.workstream_name) {
                <div class="absolute bottom-0 flex h-full items-end justify-center" [style.left.%]="chartLeft($index)" [style.width.%]="chartWidth()">
                  <div class="flex h-full w-full max-w-12 items-end justify-center gap-1">
                    <div class="w-4 bg-[var(--t-blue-light)]" [style.height.%]="chartHeight(row.bankable_plan_amount)" title="Locked baseline"></div>
                    <div class="w-4 bg-emerald-500" [style.height.%]="chartHeight(row.actual_amount)" title="Realized"></div>
                  </div>
                </div>
              }
            </div>
            <div class="mt-3 grid gap-2" [style.grid-template-columns]="'repeat(' + Math.max(summary().workstreams.length, 1) + ', minmax(0, 1fr))'">
              @for (row of summary().workstreams; track row.workstream_id || row.workstream_name) {
                <p class="truncate text-center text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]" [title]="row.workstream_name">
                  {{ row.workstream_name }}
                </p>
              }
            </div>
          </div>

          <div class="space-y-3">
            @for (row of summary().workstreams; track row.workstream_id || row.workstream_name) {
              <button
                type="button"
                class="w-full border border-[var(--t-border)] bg-[var(--t-surface)] p-3 text-left hover:border-[var(--t-accent)]"
                (click)="drillToWorkstream(row.workstream_id)"
                [attr.aria-label]="'View benefits for ' + row.workstream_name">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ row.workstream_name }}</p>
                    <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      {{ row.locked_initiative_count }}/{{ row.initiative_count }} locked
                    </p>
                  </div>
                  <p class="text-right text-sm font-black text-[var(--t-text-primary)]">{{ formatMoney(row.bankable_plan_amount) }}</p>
                </div>
                <div class="mt-3 h-1.5 bg-[var(--t-border)]">
                  <div class="h-full bg-emerald-500" [style.width.%]="realizationPct(row.actual_amount, row.bankable_plan_amount)"></div>
                </div>
              </button>
            } @empty {
              <p class="border border-[var(--t-border)] p-4 text-sm font-bold text-[var(--t-text-secondary)]">No workstream benefit data is available.</p>
            }
          </div>
        </div>
      </section>

      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
          <div>
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative contributors</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Bankable plan baseline by initiative</h2>
          </div>
          <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
            {{ summary().initiatives.length }} rows
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[980px] text-left text-xs">
            <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              <tr>
                <th class="px-4 py-3">Initiative</th>
                <th class="px-4 py-3">Workstream</th>
                <th class="px-4 py-3">Stage</th>
                <th class="px-4 py-3 text-right">Locked baseline</th>
                <th class="px-4 py-3 text-right">Actual</th>
                <th class="px-4 py-3 text-right">Variance</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (row of summary().initiatives; track row.initiative_id) {
                <tr class="hover:bg-[var(--t-surface-raised)]">
                  <td class="px-4 py-3">
                    <a [routerLink]="['/initiatives', row.initiative_id, 'bankable-plan']" class="font-black text-[var(--t-text-primary)] hover:text-[var(--t-accent)]">
                      {{ row.initiative_code || 'INIT' }} - {{ row.name }}
                    </a>
                    <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      {{ row.locked_bankable_plan_version ? 'Bankable v' + row.locked_bankable_plan_version : 'No locked plan' }}
                    </p>
                  </td>
                  <td class="px-4 py-3 font-bold text-[var(--t-text-secondary)]">{{ row.workstream_name || 'Unassigned' }}</td>
                  <td class="px-4 py-3 font-bold capitalize text-[var(--t-text-secondary)]">{{ row.stage || 'unknown' }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ formatMoney(row.bankable_plan_amount) }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ formatMoney(row.actual_amount) }}</td>
                  <td class="px-4 py-3 text-right font-black" [class.text-emerald-600]="delta(row.actual_amount, row.bankable_plan_amount) >= 0" [class.text-red-500]="delta(row.actual_amount, row.bankable_plan_amount) < 0">
                    {{ formatMoney(row.variance) }}
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="6" class="px-4 py-8 text-sm font-bold text-[var(--t-text-secondary)]">
                    No initiatives are available for the selected benefit scope.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
          <div>
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Ledger detail</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ granularityLabel() }} periods</h2>
          </div>
          <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
            {{ summary().periods.length }} rows
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[860px] text-left text-xs">
            <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              <tr>
                <th class="px-4 py-3">Period</th>
                <th class="px-4 py-3">Range</th>
                <th class="px-4 py-3 text-right">Plan</th>
                <th class="px-4 py-3 text-right">Actual</th>
                <th class="px-4 py-3 text-right">Variance</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (period of summary().periods; track period.period) {
                <tr class="hover:bg-[var(--t-surface-raised)]">
                  <td class="px-4 py-3 font-black text-[var(--t-text-primary)]">{{ period.period }}</td>
                  <td class="px-4 py-3 text-[var(--t-text-secondary)]">
                    {{ periodRangeLabel(period.period_start, period.period_end) }}
                  </td>
                  <td class="px-4 py-3 text-right font-bold">{{ formatMoney(period.bankable_plan_amount) }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ formatMoney(period.actual_amount) }}</td>
                  <td class="px-4 py-3 text-right font-black" [class.text-emerald-600]="delta(period.actual_amount, period.bankable_plan_amount) >= 0" [class.text-red-500]="delta(period.actual_amount, period.bankable_plan_amount) < 0">
                    {{ formatMoney(period.variance) }}
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="px-4 py-8 text-sm font-bold text-[var(--t-text-secondary)]">
                    No benefit ledger rows are available for the selected granularity.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
      }

      @if (activeTab() === 'ledger') {
        <section class="grid gap-4 xl:grid-cols-[22rem_minmax(0,1fr)]">
          <aside class="card p-5">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              {{ ledgerForm().id ? 'Edit ledger row' : 'Add ledger row' }}
            </p>
            <div class="mt-4 space-y-3">
              <label class="block">
                <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative</span>
                <select class="input-field mt-1 w-full py-2 text-xs" [ngModel]="selectedInitiativeId()" (ngModelChange)="setSelectedInitiative($event)" aria-label="Ledger initiative">
                  @for (initiative of initiatives(); track initiative.id) {
                    <option [value]="initiative.id">{{ initiativeLabel(initiative) }}</option>
                  }
                </select>
              </label>
              <label class="block">
                <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Granularity</span>
                <select class="input-field mt-1 w-full py-2 text-xs" [ngModel]="ledgerForm().period_granularity" (ngModelChange)="updateLedgerForm('period_granularity', $event)" aria-label="Ledger granularity">
                  @for (option of granularities; track option.id) {
                    <option [value]="option.id">{{ option.label }}</option>
                  }
                </select>
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Start</span>
                  <input type="date" class="input-field mt-1 w-full py-2 text-xs" [ngModel]="ledgerForm().period_start" (ngModelChange)="updateLedgerForm('period_start', $event)" aria-label="Ledger period start">
                </label>
                <label class="block">
                  <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">End</span>
                  <input type="date" class="input-field mt-1 w-full py-2 text-xs" [ngModel]="ledgerForm().period_end" (ngModelChange)="updateLedgerForm('period_end', $event)" aria-label="Ledger period end">
                </label>
              </div>
              <label class="block">
                <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Actual amount</span>
                <input type="number" step="0.0001" class="input-field mt-1 w-full py-2 text-xs" [ngModel]="ledgerForm().actual_amount" (ngModelChange)="updateLedgerForm('actual_amount', $event)" aria-label="Ledger actual amount">
              </label>
              <label class="block">
                <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Description</span>
                <textarea rows="4" class="input-field mt-1 w-full text-xs" [ngModel]="ledgerForm().description" (ngModelChange)="updateLedgerForm('description', $event)" aria-label="Ledger description"></textarea>
              </label>
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3 text-xs font-bold text-[var(--t-text-secondary)]">
                The locked bankable plan amount is calculated by the system from the selected initiative and period.
              </div>
              <div class="flex gap-2">
                <button type="button" class="btn-primary flex-1 text-[10px]" [disabled]="savingLedger()" (click)="saveLedgerEntry()" aria-label="Save benefit ledger row">
                  {{ ledgerForm().id ? 'Update' : 'Create' }}
                </button>
                <button type="button" class="btn-ghost text-[10px]" (click)="resetLedgerForm()" aria-label="Clear benefit ledger form">Clear</button>
              </div>
            </div>
          </aside>

          <section class="card overflow-hidden">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Ledger entries</p>
                <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ selectedInitiativeLabel() }}</h2>
              </div>
              <select class="input-field min-w-72 py-2 text-xs" [ngModel]="selectedInitiativeId()" (ngModelChange)="setSelectedInitiative($event)" aria-label="Select initiative for ledger entries">
                @for (initiative of initiatives(); track initiative.id) {
                  <option [value]="initiative.id">{{ initiativeLabel(initiative) }}</option>
                }
              </select>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full min-w-[900px] text-left text-xs">
                <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                  <tr>
                    <th class="px-4 py-3">Period</th>
                    <th class="px-4 py-3">Range</th>
                    <th class="px-4 py-3 text-right">Locked plan</th>
                    <th class="px-4 py-3 text-right">Actual</th>
                    <th class="px-4 py-3 text-right">Variance</th>
                    <th class="px-4 py-3">Description</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--t-border)]">
                  @for (entry of ledgerEntries(); track entry.id) {
                    <tr class="hover:bg-[var(--t-surface-raised)]">
                      <td class="px-4 py-3 font-black uppercase text-[var(--t-text-primary)]">{{ entry.period_granularity }}</td>
                      <td class="px-4 py-3 font-bold text-[var(--t-text-secondary)]">{{ periodRangeLabel(entry.period_start, entry.period_end) }}</td>
                      <td class="px-4 py-3 text-right font-bold">{{ formatMoney(entry.bankable_plan_amount) }}</td>
                      <td class="px-4 py-3 text-right font-bold">{{ formatMoney(entry.actual_amount) }}</td>
                      <td class="px-4 py-3 text-right font-black" [class.text-emerald-600]="delta(entry.actual_amount, entry.bankable_plan_amount) >= 0" [class.text-red-500]="delta(entry.actual_amount, entry.bankable_plan_amount) < 0">{{ formatMoney(entry.variance) }}</td>
                      <td class="max-w-72 px-4 py-3 text-[var(--t-text-secondary)]">{{ entry.description || '-' }}</td>
                      <td class="px-4 py-3 text-right">
                        <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="editLedgerEntry(entry)" aria-label="Edit benefit ledger row">Edit</button>
                        <button type="button" class="btn-ghost px-3 py-2 text-[10px] text-red-500" (click)="deleteLedgerEntry(entry)" aria-label="Delete benefit ledger row">Delete</button>
                      </td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="7" class="px-4 py-8 text-sm font-bold text-[var(--t-text-secondary)]">
                        No ledger entries exist for the selected initiative.
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        </section>
      }

      @if (activeTab() === 'import') {
        <section class="grid gap-4 xl:grid-cols-[24rem_minmax(0,1fr)]">
          <aside class="card p-5">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">CSV import</p>
            <h2 class="mt-2 text-xl font-black text-[var(--t-text-primary)]">Import actual realization</h2>
            <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">
              Upload actual benefit realization rows by initiative code. Locked plan amounts are derived from each initiative's bankable plan.
            </p>
            <div class="mt-5 space-y-3">
              <button type="button" class="btn-secondary w-full text-[10px]" (click)="downloadTemplate()" aria-label="Download benefit ledger CSV template">Download template</button>
              <input type="file" accept=".csv,text/csv" class="input-field w-full py-2 text-xs" (change)="onImportFileSelected($event)" aria-label="Select benefit ledger CSV file">
              <button type="button" class="btn-primary w-full text-[10px]" [disabled]="!importFile() || importing()" (click)="importLedger()" aria-label="Import benefit ledger CSV">Import CSV</button>
            </div>
          </aside>

          <section class="card overflow-hidden">
            <div class="border-b border-[var(--t-border)] p-5">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Import result</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Created / updated / errors</h2>
            </div>
            @if (importResult()) {
              <div class="grid gap-4 p-5 md:grid-cols-3">
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Created</p>
                  <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ importResult()?.created }}</p>
                </div>
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Updated</p>
                  <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ importResult()?.updated }}</p>
                </div>
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Errors</p>
                  <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ importResult()?.errors?.length || 0 }}</p>
                </div>
              </div>
              @if ((importResult()?.errors?.length || 0) > 0) {
                <div class="overflow-x-auto border-t border-[var(--t-border)]">
                  <table class="w-full min-w-[720px] text-left text-xs">
                    <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      <tr>
                        <th class="px-4 py-3">Row</th>
                        <th class="px-4 py-3">Initiative</th>
                        <th class="px-4 py-3">Message</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-[var(--t-border)]">
                      @for (item of importResult()?.errors || []; track item.row) {
                        <tr>
                          <td class="px-4 py-3 font-black">{{ item.row }}</td>
                          <td class="px-4 py-3 font-bold">{{ item.initiative_code || '-' }}</td>
                          <td class="px-4 py-3 text-[var(--t-text-secondary)]">{{ item.message }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            } @else {
              <p class="p-8 text-sm font-bold text-[var(--t-text-secondary)]">
                No import has been run in this session.
              </p>
            }
          </section>
        </section>
      }
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }
  `],
})
export class BenefitTrackingComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly initiativeLabel = initiativeLabel;
  readonly formatMoney = formatMoney;
  readonly delta = delta;
  readonly Math = Math;

  readonly initiatives = signal<InitiativeOption[]>([]);
  readonly workstreams = signal<WorkstreamOption[]>([]);
  readonly activeTab = signal<BenefitTrackingTab>('summary');
  readonly scope = signal<BenefitScope>('portfolio');
  readonly selectedInitiativeId = signal('');
  readonly selectedWorkstreamId = signal('');
  readonly selectedInitiative = computed(() => this.initiatives().find(item => item.id === this.selectedInitiativeId()) || null);
  readonly selectedInitiativeLabel = computed(() => initiativeLabel(this.selectedInitiative()));
  readonly granularity = signal<FinancialLedgerGranularity>('monthly');
  readonly summary = signal<BenefitLedgerRollupSummaryResponse>(this.emptySummary('Portfolio', 'portfolio'));
  readonly ledgerEntries = signal<BenefitLedgerEntry[]>([]);
  readonly ledgerForm = signal<BenefitLedgerForm>(this.emptyLedgerForm());
  readonly savingLedger = signal(false);
  readonly importFile = signal<File | null>(null);
  readonly importResult = signal<BenefitLedgerImportResult | null>(null);
  readonly importing = signal(false);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<string | null>(null);

  readonly tabs: Array<{ id: BenefitTrackingTab; label: string }> = [
    { id: 'summary', label: 'Summary' },
    { id: 'ledger', label: 'Ledger Entries' },
    { id: 'import', label: 'Import' },
  ];

  readonly granularities: Array<{ id: FinancialLedgerGranularity; label: string }> = [
    { id: 'weekly', label: 'Weekly' },
    { id: 'monthly', label: 'Monthly' },
    { id: 'yearly', label: 'Yearly' },
  ];

  ngOnInit(): void {
    this.loadOptions();
  }

  setActiveTab(tab: BenefitTrackingTab): void {
    this.activeTab.set(tab);
    this.error.set(null);
    this.success.set(null);
    if (tab === 'ledger') this.loadLedgerEntries();
  }

  setScope(next: BenefitScope): void {
    if (next === this.scope()) return;
    this.scope.set(next);
    if (next === 'workstream' && !this.selectedWorkstreamId()) {
      this.selectedWorkstreamId.set(this.workstreams()[0]?.id || '');
    }
    if (next === 'initiative' && !this.selectedInitiativeId()) {
      this.selectedInitiativeId.set(selectDefaultInitiative(this.initiatives()));
    }
    this.loadSummary();
  }

  setSelectedInitiative(initiativeId: string): void {
    if (!initiativeId || initiativeId === this.selectedInitiativeId()) return;
    this.selectedInitiativeId.set(initiativeId);
    this.resetLedgerForm();
    this.loadSummary();
    if (this.activeTab() === 'ledger') this.loadLedgerEntries();
  }

  setSelectedWorkstream(workstreamId: string): void {
    if (!workstreamId || workstreamId === this.selectedWorkstreamId()) return;
    this.selectedWorkstreamId.set(workstreamId);
    this.loadSummary();
  }

  setGranularity(next: FinancialLedgerGranularity): void {
    if (next === this.granularity()) return;
    this.granularity.set(next);
    this.loadSummary();
  }

  drillToWorkstream(workstreamId?: string | null): void {
    if (!workstreamId) return;
    this.scope.set('workstream');
    this.selectedWorkstreamId.set(workstreamId);
    this.loadSummary();
  }

  granularityLabel(): string {
    return this.granularities.find(item => item.id === this.granularity())?.label || this.granularity();
  }

  scopeLabel(): string {
    if (this.scope() === 'workstream') return 'Selected workstream';
    if (this.scope() === 'initiative') return 'Selected initiative';
    return 'Overall portfolio';
  }

  periodRangeLabel(start?: string | null, end?: string | null): string {
    if (!start && !end) return '-';
    if (!end || start === end) return formatDateOnly(start || end);
    return `${formatDateOnly(start)} -> ${formatDateOnly(end)}`;
  }

  chartWidth(): number {
    const count = Math.max(this.summary().workstreams.length, 1);
    return 100 / count;
  }

  chartLeft(index: number): number {
    return index * this.chartWidth();
  }

  chartHeight(value: string | number | null | undefined): number {
    const max = Math.max(...this.summary().workstreams.flatMap(row => [parseNumeric(row.bankable_plan_amount), parseNumeric(row.actual_amount)]), 1);
    return Math.max(2, Math.min(100, (parseNumeric(value) / max) * 100));
  }

  realizationPct(actual: string | number | null | undefined, plan: string | number | null | undefined): number {
    const baseline = parseNumeric(plan);
    if (baseline <= 0) return 0;
    return Math.max(0, Math.min(100, (parseNumeric(actual) / baseline) * 100));
  }

  updateLedgerForm<K extends keyof BenefitLedgerForm>(key: K, value: BenefitLedgerForm[K]): void {
    this.ledgerForm.update(current => ({ ...current, [key]: value }));
  }

  editLedgerEntry(entry: BenefitLedgerEntry): void {
    this.ledgerForm.set({
      id: entry.id,
      initiative_id: entry.initiative_id,
      period_granularity: entry.period_granularity,
      period_start: entry.period_start,
      period_end: entry.period_end,
      actual_amount: entry.actual_amount,
      description: entry.description || '',
    });
  }

  resetLedgerForm(): void {
    this.ledgerForm.set(this.emptyLedgerForm());
  }

  saveLedgerEntry(): void {
    const form = this.ledgerForm();
    if (!form.initiative_id || !form.period_start || !form.period_end) {
      this.error.set('Select an initiative and period before saving.');
      return;
    }
    this.savingLedger.set(true);
    this.error.set(null);
    this.success.set(null);
    const body = {
      period_granularity: form.period_granularity,
      period_start: form.period_start,
      period_end: form.period_end,
      actual_amount: form.actual_amount || '0',
      description: form.description || null,
    };
    const request = form.id
      ? this.api.put<BenefitLedgerEntry>(`/initiatives/${form.initiative_id}/benefit-ledger/${form.id}`, body)
      : this.api.post<BenefitLedgerEntry>(`/initiatives/${form.initiative_id}/benefit-ledger`, body);
    request.subscribe({
      next: () => {
        this.savingLedger.set(false);
        this.success.set(form.id ? 'Benefit ledger row updated.' : 'Benefit ledger row created.');
        this.resetLedgerForm();
        this.loadLedgerEntries();
        this.loadSummary();
      },
      error: err => {
        this.savingLedger.set(false);
        this.error.set(err?.error?.detail || 'Could not save benefit ledger row.');
      },
    });
  }

  deleteLedgerEntry(entry: BenefitLedgerEntry): void {
    if (!confirm('Delete this benefit ledger row?')) return;
    this.error.set(null);
    this.success.set(null);
    this.api.delete<void>(`/initiatives/${entry.initiative_id}/benefit-ledger/${entry.id}`).subscribe({
      next: () => {
        this.success.set('Benefit ledger row deleted.');
        this.loadLedgerEntries();
        this.loadSummary();
      },
      error: err => this.error.set(err?.error?.detail || 'Could not delete benefit ledger row.'),
    });
  }

  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.importFile.set(input.files?.[0] || null);
  }

  importLedger(): void {
    const file = this.importFile();
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    this.importing.set(true);
    this.error.set(null);
    this.success.set(null);
    this.api.postForm<BenefitLedgerImportResult>('/benefit-ledger/import', form).subscribe({
      next: result => {
        this.importResult.set(result);
        this.importing.set(false);
        this.success.set(`Import finished: ${result.created} created, ${result.updated} updated, ${result.errors.length} errors.`);
        this.loadSummary();
        if (this.activeTab() === 'ledger') this.loadLedgerEntries();
      },
      error: err => {
        this.importing.set(false);
        this.error.set(err?.error?.detail || 'Could not import benefit ledger CSV.');
      },
    });
  }

  downloadTemplate(): void {
    const csv = [
      'initiative_code,period_granularity,period_start,period_end,actual_amount,description',
      'ENT-001,monthly,2028-01-01,2028-01-31,0.0000,January realized benefit',
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'benefit-ledger-import-template.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  private loadOptions(): void {
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe({
      next: response => {
        const items = (response.items || []) as InitiativeOption[];
        this.initiatives.set(items);
        this.selectedInitiativeId.set(selectDefaultInitiative(items, this.selectedInitiativeId() || null));
        this.workstreams.set(this.deriveWorkstreams(items));
        this.selectedWorkstreamId.set(this.workstreams()[0]?.id || '');
        this.resetLedgerForm();
        this.loadSummary();
      },
      error: err => this.error.set(err?.error?.detail || 'Could not load initiatives.'),
    });
  }

  private loadSummary(): void {
    this.loading.set(true);
    this.error.set(null);

    if (this.scope() === 'initiative') {
      this.loadInitiativeSummary();
      return;
    }

    const params: Record<string, string> = { granularity: this.granularity() };
    if (this.scope() === 'workstream') {
      if (!this.selectedWorkstreamId()) {
        this.summary.set(this.emptySummary('Workstream', 'workstream'));
        this.loading.set(false);
        return;
      }
      params['workstream_id'] = this.selectedWorkstreamId();
    }

    this.api.get<BenefitLedgerRollupSummaryResponse>('/benefit-ledger/summary', params).subscribe({
      next: response => {
        this.summary.set(response);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err?.error?.detail || 'Could not load benefit tracking data.');
        this.loading.set(false);
      },
    });
  }

  private loadLedgerEntries(): void {
    const initiativeId = this.selectedInitiativeId();
    if (!initiativeId) {
      this.ledgerEntries.set([]);
      return;
    }
    this.api.get<BenefitLedgerEntry[]>(`/initiatives/${initiativeId}/benefit-ledger`).subscribe({
      next: rows => this.ledgerEntries.set(rows || []),
      error: err => this.error.set(err?.error?.detail || 'Could not load benefit ledger rows.'),
    });
  }

  private loadInitiativeSummary(): void {
    const initiativeId = this.selectedInitiativeId();
    if (!initiativeId) {
      this.summary.set(this.emptySummary('Initiative', 'initiative'));
      this.loading.set(false);
      return;
    }

    this.api.get<BenefitLedgerSummaryResponse>(`/initiatives/${initiativeId}/benefit-ledger/summary`, {
      granularity: this.granularity(),
    }).subscribe({
      next: response => {
        const initiative = this.selectedInitiative();
        const workstream = this.workstreams().find(item => item.id === initiative?.['workstream_id']);
        this.summary.set({
          scope: 'initiative',
          scope_id: initiativeId,
          scope_name: initiativeLabel(initiative),
          granularity: response.granularity,
          periods: response.periods,
          bankable_plan_amount: response.bankable_plan_amount,
          actual_amount: response.actual_amount,
          variance: response.variance,
          workstreams: [],
          initiatives: [{
            initiative_id: initiativeId,
            initiative_code: initiative?.initiative_code,
            name: initiative?.name || 'Initiative',
            stage: initiative?.stage,
            workstream_id: initiative?.['workstream_id'] || null,
            workstream_name: workstream?.name || null,
            locked_bankable_plan_version: response.locked_bankable_plan_version,
            bankable_plan_amount: response.bankable_plan_amount,
            actual_amount: response.actual_amount,
            variance: response.variance,
          }],
        });
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err?.error?.detail || 'Could not load benefit tracking data.');
        this.loading.set(false);
      },
    });
  }

  private deriveWorkstreams(items: InitiativeOption[]): WorkstreamOption[] {
    const lookup = new Map<string, WorkstreamOption>();
    for (const initiative of items) {
      const id = String(initiative['workstream_id'] || '');
      const name = String(initiative['workstreams']?.name || initiative['workstream_name'] || '');
      if (id && name) lookup.set(id, { id, name });
    }
    return [...lookup.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  private emptySummary(scopeName: string, scope: BenefitScope): BenefitLedgerRollupSummaryResponse {
    return {
      scope,
      scope_name: scopeName,
      granularity: this.granularity(),
      periods: [],
      bankable_plan_amount: '0.0000',
      actual_amount: '0.0000',
      variance: '0.0000',
      workstreams: [],
      initiatives: [],
    };
  }

  private emptyLedgerForm(): BenefitLedgerForm {
    const selected = this.selectedInitiativeId?.() || '';
    return {
      initiative_id: selected,
      period_granularity: this.granularity?.() || 'monthly',
      period_start: '',
      period_end: '',
      actual_amount: '0.0000',
      description: '',
    };
  }
}
