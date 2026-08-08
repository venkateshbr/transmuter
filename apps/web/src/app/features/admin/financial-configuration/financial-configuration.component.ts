import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { FinancialConfigurationFacade } from './financial-configuration.facade';
import {
  FinancialAttributeDefinition,
  FinancialBridgeRow,
  FinancialCostCategory,
  FinancialMetricDefinition,
  FinancialMetricDeletionCategory,
  FinancialMetricDeletionImpact,
  FinancialReportingSettings,
  FinancialScenario,
  FinancialSubtab,
} from './financial-configuration.models';
import { financialKeyError, formulaIdentifiers, uniqueFinancialKey } from './financial-key.util';

const DEFAULT_SETTINGS: FinancialReportingSettings = {
  fiscal_year_start_month: 1,
  reporting_currency: '',
  recurring_cost_inflation_mode: 'manual_entry',
  default_annual_inflation_rate_pct: '0.0000',
  allow_cost_line_inflation_override: true,
};

@Component({
  selector: 'app-financial-configuration',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [FinancialConfigurationFacade],
  template: `
    <div class="card overflow-hidden" data-testid="financial-configuration-workbench">
      <header
        class="border-b border-[var(--t-border)] bg-[var(--t-primary)] px-6 py-5 text-white md:px-8"
      >
        <p class="text-[10px] font-black uppercase tracking-[0.2em] text-[var(--t-blue-light)]">
          Tenant financial language
        </p>
        <div class="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 class="text-xl font-black">Financial Configuration</h3>
            <p class="mt-1 max-w-3xl text-xs leading-5 text-white/70">
              Keys are tenant-scoped formula identifiers. The same key may be used safely by another
              tenant, but each key must be unique within this tenant.
            </p>
          </div>
          <span
            class="border border-white/25 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-white/80"
            >{{ metrics().length }} metrics · {{ bridgeRows().length }} bridge rows</span
          >
        </div>
      </header>

      <nav
        class="overflow-x-auto border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4"
        role="tablist"
        aria-label="Financial configuration sections"
      >
        <div class="flex min-w-max">
          @for (tab of tabs; track tab.key; let index = $index) {
            <button
              type="button"
              role="tab"
              class="border-b-2 px-4 py-4 text-[10px] font-black uppercase tracking-widest"
              [class.border-[var(--t-accent)]]="activeSubtab() === tab.key"
              [class.text-[var(--t-accent)]]="activeSubtab() === tab.key"
              [class.border-transparent]="activeSubtab() !== tab.key"
              [class.text-[var(--t-text-tertiary)]]="activeSubtab() !== tab.key"
              [attr.aria-selected]="activeSubtab() === tab.key"
              [attr.data-testid]="'financial-subtab-' + tab.key"
              [attr.tabindex]="activeSubtab() === tab.key ? 0 : -1"
              (click)="activeSubtab.set(tab.key)"
              (keydown.arrowright)="moveTab(index, 1)"
              (keydown.arrowleft)="moveTab(index, -1)"
              [attr.aria-label]="'Open ' + tab.label"
            >
              {{ tab.label }}
            </button>
          }
        </div>
      </nav>

      @if (loading()) {
        <div class="p-8 text-sm font-bold text-[var(--t-text-secondary)]">
          Loading tenant financial configuration…
        </div>
      } @else {
        @if (message()) {
          <div
            class="mx-6 mt-5 border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs font-bold text-emerald-600"
            role="status"
          >
            {{ message() }}
          </div>
        }
        @if (error()) {
          <div
            class="mx-6 mt-5 border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs font-bold text-red-600"
            role="alert"
          >
            {{ error() }}
          </div>
        }

        @if (activeSubtab() === 'settings') {
          <section class="grid gap-6 p-6 md:p-8" role="tabpanel">
            <div>
              <p class="section-label">Reporting settings</p>
              <h4 class="section-title">Currency, fiscal calendar, and cost inflation</h4>
            </div>
            <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              <label class="field-label"
                >Reporting currency
                <input
                  class="input-field mt-2 w-full uppercase"
                  [ngModel]="settings().reporting_currency"
                  (ngModelChange)="patchSettings('reporting_currency', $event.toUpperCase())"
                  maxlength="3"
                  aria-label="Reporting currency"
                />
              </label>
              <label class="field-label"
                >Fiscal year starts
                <select
                  class="input-field mt-2 w-full"
                  [ngModel]="settings().fiscal_year_start_month"
                  (ngModelChange)="patchSettings('fiscal_year_start_month', numberValue($event))"
                  aria-label="Fiscal year start month"
                >
                  @for (month of fiscalMonths; track month.value) {
                    <option [ngValue]="month.value">{{ month.label }}</option>
                  }
                </select>
              </label>
              <label class="field-label"
                >Inflation mode
                <select
                  class="input-field mt-2 w-full"
                  [ngModel]="settings().recurring_cost_inflation_mode"
                  (ngModelChange)="patchSettings('recurring_cost_inflation_mode', $event)"
                  aria-label="Recurring cost inflation mode"
                >
                  <option value="manual_entry">Manual entry</option>
                  <option value="optional_per_line">Optional per line</option>
                  <option value="default_on">Default on</option>
                </select>
              </label>
              <label class="field-label"
                >Default annual inflation %
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  class="input-field mt-2 w-full"
                  [ngModel]="settings().default_annual_inflation_rate_pct"
                  (ngModelChange)="patchSettings('default_annual_inflation_rate_pct', $event)"
                  [disabled]="settings().recurring_cost_inflation_mode === 'manual_entry'"
                  aria-label="Default annual recurring cost inflation percent"
                />
              </label>
            </div>
            <div
              class="flex flex-wrap items-center justify-between gap-4 border-t border-[var(--t-border)] pt-5"
            >
              <label class="flex items-center gap-3 text-xs font-bold text-[var(--t-text-primary)]"
                ><input
                  type="checkbox"
                  [checked]="settings().allow_cost_line_inflation_override"
                  (change)="
                    patchSettings('allow_cost_line_inflation_override', $any($event.target).checked)
                  "
                  aria-label="Allow cost line inflation override"
                />Allow an inflation override on each cost line</label
              >
              <button
                type="button"
                class="btn-primary px-5 py-3 text-[10px]"
                (click)="saveSettings()"
                [disabled]="saving()"
                aria-label="Save reporting settings"
              >
                Save settings
              </button>
            </div>
          </section>
        }

        @if (activeSubtab() === 'metrics') {
          <section class="grid min-h-[560px] lg:grid-cols-[320px_minmax(0,1fr)]" role="tabpanel">
            <aside
              class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] lg:border-b-0 lg:border-r"
            >
              <div class="border-b border-[var(--t-border)] p-4">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="section-label">Metric catalog</p>
                    <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                      Select a metric to edit
                    </p>
                  </div>
                  <button
                    type="button"
                    class="btn-secondary px-3 py-2 text-[10px]"
                    (click)="addMetric()"
                    aria-label="Add metric definition"
                  >
                    Add metric
                  </button>
                </div>
                <input
                  class="input-field mt-4 w-full py-2 text-xs"
                  [ngModel]="metricSearch()"
                  (ngModelChange)="metricSearch.set($event)"
                  placeholder="Search label or key"
                  aria-label="Search metric definitions"
                />
              </div>
              <div class="max-h-[620px] overflow-y-auto">
                @for (metric of filteredMetrics(); track metric.id || metric.key) {
                  <button
                    type="button"
                    class="block w-full border-b border-[var(--t-border)] px-4 py-3 text-left"
                    [class.bg-[var(--t-surface)]]="selectedMetric() === metric"
                    (click)="selectedMetric.set(metric)"
                    [attr.aria-label]="'Edit metric ' + metric.label"
                  >
                    <span class="flex min-w-0 items-center gap-2">
                      <span
                        class="min-w-0 flex-1 truncate text-xs font-black text-[var(--t-text-primary)]"
                        >{{ metric.label }}</span
                      >
                      @if (isDefaultMetric(metric)) {
                        <span class="badge-gray shrink-0 rounded-none text-[8px]"
                          >Default metric</span
                        >
                      }
                    </span>
                    <span
                      class="mt-1 block truncate font-mono text-[10px] text-[var(--t-accent)]"
                      >{{ metric.key }}</span
                    >
                    <span
                      class="mt-2 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]"
                      >{{ metric.aggregation }} · {{ metric.value_type }} ·
                      {{ metric.is_active ? 'active' : 'hidden' }}</span
                    >
                  </button>
                }
              </div>
            </aside>
            <div class="p-5 md:p-7">
              @if (selectedMetric(); as metric) {
                <div class="grid gap-6">
                  <div
                    class="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--t-border)] pb-5"
                  >
                    <div class="min-w-0">
                      <p class="section-label">Metric editor</p>
                      <div class="mt-1 flex flex-wrap items-center gap-2">
                        <h4 class="section-title mt-0">{{ metric.label || 'New metric' }}</h4>
                        @if (isDefaultMetric(metric)) {
                          <span class="badge-gray rounded-none text-[8px]">Default metric</span>
                        }
                      </div>
                      @if (isDefaultMetric(metric)) {
                        <p class="mt-2 max-w-2xl text-xs leading-5 text-[var(--t-text-secondary)]">
                          {{ defaultMetricExplanation(metric) }} You can delete this metric when it
                          has no saved dependencies. Deleted defaults are not restored
                          automatically.
                        </p>
                      }
                    </div>
                    <div class="flex gap-2">
                      @if (!metric.id) {
                        <button
                          type="button"
                          class="btn-ghost px-3 py-2 text-[10px]"
                          (click)="discardMetric(metric)"
                          aria-label="Discard unsaved metric"
                        >
                          Discard metric
                        </button>
                      } @else {
                        <button
                          type="button"
                          class="btn-ghost px-3 py-2 text-[10px] text-red-600"
                          (click)="openMetricDeletion(metric)"
                          [disabled]="deletionLoading() || saving()"
                          [attr.aria-label]="'Delete metric ' + metric.label"
                        >
                          Delete metric
                        </button>
                      }
                      <button
                        type="button"
                        class="btn-ghost px-3 py-2 text-[10px]"
                        (click)="metric.is_active = !metric.is_active"
                        [attr.aria-label]="'Toggle ' + metric.label"
                      >
                        {{ metric.is_active ? 'Active' : 'Hidden' }}</button
                      ><button
                        type="button"
                        class="btn-primary px-4 py-2 text-[10px]"
                        (click)="saveMetric(metric)"
                        [disabled]="saving() || !!metricKeyError(metric)"
                        aria-label="Save metric definition"
                      >
                        Save metric
                      </button>
                    </div>
                  </div>
                  <div class="grid gap-5 md:grid-cols-2">
                    <label class="field-label"
                      >Display label<input
                        class="input-field mt-2 w-full"
                        [ngModel]="metric.label"
                        (ngModelChange)="updateMetricLabel(metric, $event)"
                        aria-label="Metric definition label"
                    /></label>
                    <label class="field-label"
                      >Formula key
                      <div class="mt-2 flex gap-2">
                        <input
                          class="input-field min-w-0 flex-1 font-mono text-xs"
                          [value]="metric.key"
                          (input)="updateMetricKey(metric, $any($event.target).value)"
                          [disabled]="!!metric.id"
                          aria-label="Metric formula key"
                        /><button
                          type="button"
                          class="btn-secondary px-3"
                          (click)="copyKey(metric.key)"
                          [attr.aria-label]="'Copy metric key ' + metric.key"
                        >
                          <span class="material-icons text-sm">content_copy</span>
                        </button>
                      </div>
                      <span
                        class="mt-2 block text-[10px] font-medium normal-case tracking-normal text-[var(--t-text-tertiary)]"
                        >{{
                          metric.id
                            ? 'Keys are immutable after the metric is created.'
                            : 'Generated from the label. You can edit it before the first save.'
                        }}</span
                      >
                      @if (metricKeyError(metric); as keyError) {
                        <span
                          class="mt-2 block text-[10px] font-bold normal-case tracking-normal text-red-600"
                          >{{ keyError }}</span
                        >
                      }
                    </label>
                    <label class="field-label"
                      >Value type<select
                        class="input-field mt-2 w-full"
                        [(ngModel)]="metric.value_type"
                        aria-label="Metric value type"
                      >
                        <option value="currency">Currency</option>
                        <option value="percent">Percent</option>
                        <option value="number">Number</option>
                      </select></label
                    >
                    <label class="field-label"
                      >Aggregation<select
                        class="input-field mt-2 w-full"
                        [(ngModel)]="metric.aggregation"
                        aria-label="Metric aggregation"
                      >
                        <option value="sum">Sum</option>
                        <option value="avg">Average</option>
                        <option value="last">Last</option>
                        <option value="formula">Formula</option>
                      </select></label
                    >
                    <label class="field-label"
                      >Benefit classification<select
                        class="input-field mt-2 w-full"
                        [ngModel]="metric.benefit_class || ''"
                        (ngModelChange)="updateBenefitClass(metric, $event)"
                        aria-label="Metric benefit class"
                      >
                        <option value="">Not a benefit</option>
                        <option value="revenue">Revenue</option>
                        <option value="margin">Margin</option>
                        <option value="savings">Savings</option>
                        <option value="avoidance">Avoidance</option>
                        <option value="other">Other</option>
                      </select></label
                    >
                    <label class="field-label"
                      >Display order<input
                        type="number"
                        class="input-field mt-2 w-full"
                        [(ngModel)]="metric.display_order"
                        aria-label="Metric display order"
                    /></label>
                  </div>
                  @if (metric.aggregation === 'formula') {
                    <div
                      class="border-l-4 border-[var(--t-blue-light)] bg-[var(--t-surface-raised)] p-5"
                    >
                      <p class="section-label">Formula workbench</p>
                      <label class="mt-4 block field-label"
                        >Expression<textarea
                          #formulaEditor
                          class="input-field mt-2 min-h-28 w-full resize-y font-mono text-xs leading-6"
                          [ngModel]="metric.formula || ''"
                          (ngModelChange)="updateFormula(metric, $event)"
                          placeholder="revenue_uplift / baseline_revenue * 100"
                          aria-label="Metric formula"
                        ></textarea>
                      </label>
                      <div class="mt-5">
                        <p class="field-label">Available tenant variables</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">
                          Select a key to insert it into the expression. Baseline aliases represent
                          tenant annual baselines.
                        </p>
                        <div
                          class="mt-3 flex max-h-44 flex-wrap content-start gap-2 overflow-y-auto"
                        >
                          @for (variable of availableFormulaVariables(metric); track variable.key) {
                            <button
                              type="button"
                              class="border border-[var(--t-border)] bg-[var(--t-surface)] px-2 py-1.5 text-left hover:border-[var(--t-accent)]"
                              (click)="insertFormulaKey(metric, variable.key, formulaEditor)"
                              [attr.aria-label]="'Insert formula variable ' + variable.key"
                            >
                              <span
                                class="block font-mono text-[10px] font-bold text-[var(--t-accent)]"
                                >{{ variable.key }}</span
                              ><span class="block text-[9px] text-[var(--t-text-tertiary)]">{{
                                variable.label
                              }}</span>
                            </button>
                          }
                        </div>
                      </div>
                      @if (metric.formula_inputs.length) {
                        <p class="mt-4 text-[10px] text-[var(--t-text-secondary)]">
                          <span class="font-black uppercase tracking-widest">Dependencies:</span>
                          <span class="font-mono">{{ metric.formula_inputs.join(', ') }}</span>
                        </p>
                      }
                    </div>
                  }
                </div>
              } @else {
                <p class="text-sm text-[var(--t-text-secondary)]">
                  Select a metric from the catalog.
                </p>
              }
            </div>
          </section>
        }

        @if (activeSubtab() === 'planning') {
          <section class="grid gap-8 p-6 md:p-8 xl:grid-cols-2" role="tabpanel">
            <div class="config-panel">
              <div class="panel-header">
                <div>
                  <p class="section-label">Annual baselines</p>
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                    Tenant-wide original operating metrics
                  </p>
                </div>
                <div class="flex items-end gap-2">
                  <label class="field-label"
                    >Fiscal year<input
                      type="number"
                      min="2020"
                      max="2060"
                      class="input-field mt-2 w-28 py-2"
                      [ngModel]="baselineYear()"
                      (ngModelChange)="setBaselineYear($event)"
                      aria-label="Tenant baseline fiscal year" /></label
                  ><button
                    type="button"
                    class="btn-primary px-3 py-2 text-[10px]"
                    (click)="saveBaselines()"
                    aria-label="Save tenant annual baselines"
                  >
                    Save
                  </button>
                </div>
              </div>
              <div class="grid gap-4 p-4 md:grid-cols-2">
                @for (metric of baselineMetrics(); track metric.id) {
                  <label class="field-label"
                    >{{ metric.label
                    }}<span
                      class="mt-1 block font-mono text-[9px] normal-case tracking-normal text-[var(--t-accent)]"
                      >{{ metric.key }}</span
                    ><input
                      type="number"
                      class="input-field mt-2 w-full"
                      [ngModel]="baselineValues()[metric.id!] || ''"
                      (ngModelChange)="setBaselineValue(metric.id!, $event)"
                      [attr.aria-label]="'Tenant annual baseline for ' + metric.label"
                  /></label>
                }
              </div>
            </div>
            <div class="config-panel">
              <div class="panel-header">
                <div>
                  <p class="section-label">Scenarios</p>
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                    Planning, forecast, baseline, and actual lanes
                  </p>
                </div>
                <button
                  type="button"
                  class="btn-secondary px-3 py-2 text-[10px]"
                  (click)="addScenario()"
                  aria-label="Add scenario"
                >
                  Add scenario
                </button>
              </div>
              <div class="divide-y divide-[var(--t-border)]">
                @for (scenario of scenarios(); track scenario.id || scenario.key) {
                  <div class="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_130px_auto] sm:items-end">
                    <label class="field-label"
                      >Label<input
                        class="input-field mt-2 w-full"
                        [(ngModel)]="scenario.label"
                        aria-label="Scenario label"
                      /><span
                        class="mt-1 block truncate font-mono text-[9px] normal-case tracking-normal text-[var(--t-accent)]"
                        >{{ scenario.key }}</span
                      ></label
                    ><label class="field-label"
                      >Kind<select
                        class="input-field mt-2 w-full"
                        [(ngModel)]="scenario.kind"
                        aria-label="Scenario kind"
                      >
                        <option value="baseline">Baseline</option>
                        <option value="plan">Plan</option>
                        <option value="forecast">Forecast</option>
                        <option value="actual">Actual</option>
                      </select></label
                    ><button
                      type="button"
                      class="btn-primary px-3 py-2 text-[10px]"
                      (click)="saveScenario(scenario)"
                      aria-label="Save scenario"
                    >
                      Save
                    </button>
                  </div>
                }
              </div>
            </div>
          </section>
        }

        @if (activeSubtab() === 'bridge') {
          <section class="grid min-h-[560px] lg:grid-cols-[300px_minmax(0,1fr)]" role="tabpanel">
            <aside
              class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] lg:border-b-0 lg:border-r"
            >
              <div class="panel-header">
                <div>
                  <p class="section-label">Bridge rows</p>
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                    {{ bridgeRows().length }} reporting lines
                  </p>
                </div>
                <button
                  type="button"
                  class="btn-secondary px-3 py-2 text-[10px]"
                  (click)="addBridgeRow()"
                  aria-label="Add value bridge row"
                >
                  Add row
                </button>
              </div>
              <div class="max-h-[650px] overflow-y-auto">
                @for (row of bridgeRows(); track row.id || row.key) {
                  <button
                    type="button"
                    class="block w-full border-b border-[var(--t-border)] p-4 text-left"
                    [class.bg-[var(--t-surface)]]="selectedBridgeRow() === row"
                    (click)="selectedBridgeRow.set(row)"
                    [attr.aria-label]="'Edit value bridge row ' + row.label"
                  >
                    <span class="block text-xs font-black text-[var(--t-text-primary)]">{{
                      row.label
                    }}</span
                    ><span
                      class="mt-1 block truncate font-mono text-[10px] text-[var(--t-accent)]"
                      >{{ row.key }}</span
                    ><span
                      class="mt-2 block text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]"
                      >{{ bridgeKindLabel(row.row_kind) }} · {{ bridgeInputCount(row) }} inputs ·
                      {{ row.is_active ? 'active' : 'hidden' }}</span
                    >
                  </button>
                }
              </div>
            </aside>
            <div class="p-5 md:p-7">
              @if (selectedBridgeRow(); as row) {
                <div class="grid gap-6">
                  <div
                    class="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--t-border)] pb-5"
                  >
                    <div>
                      <p class="section-label">Value bridge editor</p>
                      <h4 class="section-title">{{ row.label }}</h4>
                    </div>
                    <div class="flex gap-2">
                      <button
                        type="button"
                        class="btn-ghost px-3 py-2 text-[10px]"
                        (click)="row.is_active = !row.is_active"
                        [attr.aria-label]="'Toggle ' + row.label"
                      >
                        {{ row.is_active ? 'Active' : 'Hidden' }}</button
                      ><button
                        type="button"
                        class="btn-primary px-4 py-2 text-[10px]"
                        (click)="saveBridgeRow(row)"
                        [disabled]="saving() || !!bridgeKeyError(row)"
                        aria-label="Save value bridge row"
                      >
                        Save row
                      </button>
                    </div>
                  </div>
                  <div
                    class="grid gap-5 md:grid-cols-2 xl:grid-cols-[minmax(320px,2fr)_minmax(220px,1fr)_140px_110px]"
                  >
                    <label class="field-label"
                      >Display label<input
                        class="input-field mt-2 w-full"
                        [ngModel]="row.label"
                        (ngModelChange)="updateBridgeLabel(row, $event)"
                        aria-label="Bridge row label"
                    /></label>
                    <label class="field-label"
                      >Row key<input
                        class="input-field mt-2 w-full font-mono text-xs"
                        [value]="row.key"
                        (input)="updateBridgeKey(row, $any($event.target).value)"
                        [disabled]="!!row.id"
                        aria-label="Bridge row key"
                      />
                      @if (bridgeKeyError(row); as keyError) {
                        <span
                          class="mt-2 block text-[10px] font-bold normal-case tracking-normal text-red-600"
                          >{{ keyError }}</span
                        >
                      }
                    </label>
                    <label class="field-label"
                      >Kind<select
                        class="input-field mt-2 w-full"
                        [(ngModel)]="row.row_kind"
                        (ngModelChange)="normalizeBridgeRow(row)"
                        aria-label="Bridge row kind"
                      >
                        <option value="metric_set">Metrics</option>
                        <option value="cost_set">Costs</option>
                        <option value="subtotal">Subtotal</option>
                        <option value="net">Net</option>
                      </select></label
                    >
                    <label class="field-label"
                      >Order<input
                        type="number"
                        class="input-field mt-2 w-full"
                        [(ngModel)]="row.display_order"
                        aria-label="Bridge row display order"
                    /></label>
                  </div>
                  <label class="field-label max-w-44"
                    >Sign<select
                      class="input-field mt-2 w-full"
                      [(ngModel)]="row.sign"
                      aria-label="Bridge row sign"
                    >
                      <option [ngValue]="1">Positive</option>
                      <option [ngValue]="-1">Negative</option>
                    </select></label
                  >
                  @if (row.row_kind === 'net') {
                    <div
                      class="border-l-4 border-[var(--t-blue-light)] bg-[var(--t-surface-raised)] p-4 text-xs text-[var(--t-text-secondary)]"
                    >
                      Net rows calculate from the bridge automatically and do not accept metric or
                      cost inputs.
                    </div>
                  } @else {
                    <div class="grid gap-5 xl:grid-cols-2">
                      <div class="config-panel">
                        <div class="panel-header">
                          <div>
                            <p class="section-label">Metric inputs</p>
                            <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                              Choose tenant metrics included in this row
                            </p>
                          </div>
                        </div>
                        <div class="grid max-h-72 gap-2 overflow-y-auto p-4 sm:grid-cols-2">
                          @for (metric of metrics(); track metric.id || metric.key) {
                            <label
                              class="flex items-start gap-2 border border-[var(--t-border)] p-2 text-xs font-bold text-[var(--t-text-primary)]"
                              ><input
                                type="checkbox"
                                class="mt-0.5"
                                [checked]="row.metric_definition_ids.includes(metric.id || '')"
                                (change)="toggleMetric(row, metric.id || '')"
                                [attr.aria-label]="'Use metric ' + metric.label + ' in bridge row'"
                              /><span class="min-w-0"
                                ><span class="block truncate">{{ metric.label }}</span
                                ><span
                                  class="block truncate font-mono text-[9px] font-normal text-[var(--t-accent)]"
                                  >{{ metric.key }}</span
                                ></span
                              ></label
                            >
                          }
                        </div>
                      </div>
                      <div class="config-panel">
                        <div class="panel-header">
                          <div>
                            <p class="section-label">Cost inputs</p>
                            <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                              Choose cost categories included in this row
                            </p>
                          </div>
                        </div>
                        <div class="grid max-h-72 gap-2 overflow-y-auto p-4 sm:grid-cols-2">
                          @for (
                            category of activeCostCategories();
                            track category.id || category.key
                          ) {
                            <label
                              class="flex items-start gap-2 border border-[var(--t-border)] p-2 text-xs font-bold text-[var(--t-text-primary)]"
                              ><input
                                type="checkbox"
                                class="mt-0.5"
                                [checked]="row.cost_category_ids.includes(category.id || '')"
                                (change)="toggleCostCategory(row, category.id || '')"
                                [attr.aria-label]="
                                  'Use cost category ' + category.label + ' in bridge row'
                                "
                              /><span class="min-w-0"
                                ><span class="block truncate">{{ category.label }}</span
                                ><span
                                  class="block truncate font-mono text-[9px] font-normal text-[var(--t-accent)]"
                                  >{{ category.key }}</span
                                ></span
                              ></label
                            >
                          }
                        </div>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          </section>
        }

        @if (activeSubtab() === 'taxonomy') {
          <section class="grid gap-8 p-6 md:p-8 xl:grid-cols-2" role="tabpanel">
            <div class="config-panel">
              <div class="panel-header">
                <div>
                  <p class="section-label">Cost categories</p>
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                    Taxonomy for cost lines and bridge rows
                  </p>
                </div>
                <button
                  type="button"
                  class="btn-secondary px-3 py-2 text-[10px]"
                  (click)="addCostCategory()"
                  aria-label="Add cost category"
                >
                  Add category
                </button>
              </div>
              <div class="divide-y divide-[var(--t-border)]">
                @for (category of costCategories(); track category.id || category.key) {
                  <div class="grid gap-3 p-4">
                    <label class="field-label"
                      >Label<input
                        class="input-field mt-2 w-full"
                        [(ngModel)]="category.label"
                        aria-label="Cost category label"
                    /></label>
                    <div class="grid gap-3 sm:grid-cols-2">
                      <label class="field-label"
                        >Key<input
                          class="input-field mt-2 w-full font-mono text-xs"
                          [(ngModel)]="category.key"
                          [disabled]="!!category.id"
                          aria-label="Cost category key" /></label
                      ><label class="field-label"
                        >Rollup<select
                          class="input-field mt-2 w-full"
                          [(ngModel)]="category.rollup_type"
                          aria-label="Cost category rollup"
                        >
                          <option [ngValue]="null">Unclassified</option>
                          <option value="recurring_cost">Recurring</option>
                          <option value="one_off_cost">One-time</option>
                          <option value="total_cost">Total cost</option>
                        </select></label
                      >
                    </div>
                    <div class="flex justify-end">
                      <button
                        type="button"
                        class="btn-primary px-3 py-2 text-[10px]"
                        (click)="saveCostCategory(category)"
                        aria-label="Save cost category"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
            <div class="config-panel">
              <div class="panel-header">
                <div>
                  <p class="section-label">Line attributes</p>
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                    Reusable fields for benefit and cost lines
                  </p>
                </div>
                <button
                  type="button"
                  class="btn-secondary px-3 py-2 text-[10px]"
                  (click)="addAttribute()"
                  aria-label="Add financial line attribute"
                >
                  Add attribute
                </button>
              </div>
              <div class="divide-y divide-[var(--t-border)]">
                @for (attribute of attributes(); track attribute.id || attribute.key) {
                  <div class="grid gap-3 p-4">
                    <label class="field-label"
                      >Label<input
                        class="input-field mt-2 w-full"
                        [(ngModel)]="attribute.label"
                        aria-label="Attribute label"
                    /></label>
                    <div class="grid gap-3 sm:grid-cols-2">
                      <label class="field-label"
                        >Applies to<select
                          class="input-field mt-2 w-full"
                          [(ngModel)]="attribute.entity_type"
                          aria-label="Attribute entity type"
                        >
                          <option value="benefit_line">Benefit lines</option>
                          <option value="cost_line">Cost lines</option>
                        </select></label
                      ><label class="field-label"
                        >Value type<select
                          class="input-field mt-2 w-full"
                          [(ngModel)]="attribute.value_type"
                          aria-label="Attribute value type"
                        >
                          <option value="text">Text</option>
                          <option value="number">Number</option>
                          <option value="currency">Currency</option>
                          <option value="percent">Percent</option>
                          <option value="date">Date</option>
                          <option value="select">Select</option>
                          <option value="boolean">Boolean</option>
                        </select></label
                      >
                    </div>
                    @if (attribute.value_type === 'select') {
                      <label class="field-label"
                        >Options<input
                          class="input-field mt-2 w-full"
                          [ngModel]="attribute.options.join(', ')"
                          (ngModelChange)="setAttributeOptions(attribute, $event)"
                          aria-label="Attribute select options"
                      /></label>
                    }
                    <div class="flex justify-end">
                      <button
                        type="button"
                        class="btn-primary px-3 py-2 text-[10px]"
                        (click)="saveAttribute(attribute)"
                        aria-label="Save attribute definition"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
          </section>
        }
      }

      @if (deletionMetric(); as metric) {
        <div
          class="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="metric-deletion-title"
          tabindex="-1"
          (keydown.escape)="closeMetricDeletion()"
          (keydown.tab)="trapDeletionFocus($event)"
          data-testid="metric-deletion-dialog"
        >
          <section
            class="max-h-[90vh] w-full max-w-3xl overflow-y-auto border border-[var(--t-border-strong)] bg-[var(--t-surface)] shadow-2xl"
          >
            <header
              class="border-b border-[var(--t-border)] bg-[var(--t-primary)] px-5 py-4 text-white"
            >
              <p
                class="text-[9px] font-black uppercase tracking-[0.18em] text-[var(--t-blue-light)]"
              >
                Dependency check
              </p>
              <h3 id="metric-deletion-title" class="mt-1 text-lg font-black">
                Delete {{ metric.label }}
              </h3>
              <p class="mt-1 font-mono text-[10px] text-white/70">{{ metric.key }}</p>
            </header>

            @if (deletionLoading()) {
              <p class="p-6 text-sm font-bold text-[var(--t-text-secondary)]" role="status">
                Checking every financial dependency…
              </p>
            } @else if (deletionImpact(); as impact) {
              <div class="grid gap-5 p-5 md:p-6">
                @if (impact.blocker_total > 0) {
                  <div class="border-l-4 border-red-600 bg-red-500/10 px-4 py-3" role="alert">
                    <p class="text-xs font-black uppercase tracking-wider text-red-600">
                      Deletion blocked
                    </p>
                    <p class="mt-1 text-xs leading-5 text-[var(--t-text-secondary)]">
                      This metric still supports {{ impact.blocker_total }} saved reference{{
                        impact.blocker_total === 1 ? '' : 's'
                      }}. Remove those references first, or hide the metric to preserve history.
                    </p>
                  </div>

                  <div class="divide-y divide-[var(--t-border)] border border-[var(--t-border)]">
                    @for (blocker of deletionBlockers(); track blocker.key) {
                      <div class="grid gap-2 px-4 py-3 sm:grid-cols-[180px_minmax(0,1fr)]">
                        <div>
                          <p
                            class="text-[10px] font-black uppercase tracking-wider text-[var(--t-text-primary)]"
                          >
                            {{ blocker.label }}
                          </p>
                          <p class="mt-1 font-mono text-xs text-red-600">
                            {{ blocker.category.count }}
                          </p>
                        </div>
                        <ul class="grid gap-1 text-xs text-[var(--t-text-secondary)]">
                          @for (reference of blocker.category.references; track reference.id) {
                            <li>
                              {{ reference.initiative_name ? reference.initiative_name + ' · ' : ''
                              }}{{ reference.label }}
                            </li>
                          }
                          @if (blocker.category.count > blocker.category.references.length) {
                            <li class="font-bold">
                              +
                              {{ blocker.category.count - blocker.category.references.length }} more
                            </li>
                          }
                        </ul>
                      </div>
                    }
                  </div>
                } @else {
                  <div
                    class="border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3"
                  >
                    <p
                      class="text-xs font-black uppercase tracking-wider text-[var(--t-text-primary)]"
                    >
                      No surviving dependencies
                    </p>
                    <p class="mt-1 text-xs leading-5 text-[var(--t-text-secondary)]">
                      Deletion is permanent. The metric key becomes available for reuse in this
                      tenant.
                    </p>
                  </div>
                }

                @if (isDefaultMetric(metric)) {
                  <div
                    class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3"
                  >
                    <p
                      class="text-[10px] font-black uppercase tracking-wider text-[var(--t-text-primary)]"
                    >
                      Default catalogue metric
                    </p>
                    <p class="mt-1 text-xs leading-5 text-[var(--t-text-secondary)]">
                      This metric was supplied as a starting point for your tenant. Deleting it does
                      not restore it automatically, and the same formula key can be recreated later.
                    </p>
                  </div>
                }

                @if (impact.cleanup.tenant_annual_baselines.count > 0) {
                  <div class="border border-amber-500/40 bg-amber-500/10 px-4 py-3">
                    <p class="text-[10px] font-black uppercase tracking-wider text-amber-700">
                      Automatic cleanup
                    </p>
                    <p class="mt-1 text-xs text-[var(--t-text-secondary)]">
                      {{ impact.cleanup.tenant_annual_baselines.count }} tenant annual baseline
                      row{{ impact.cleanup.tenant_annual_baselines.count === 1 ? '' : 's' }} will
                      also be deleted.
                    </p>
                  </div>
                }

                @if (impact.can_delete) {
                  <label class="field-label">
                    Type
                    <span class="font-mono text-[var(--t-accent)]">{{
                      impact.confirmation_key
                    }}</span>
                    to confirm
                    <input
                      class="input-field mt-2 w-full font-mono"
                      [ngModel]="deletionConfirmation()"
                      (ngModelChange)="deletionConfirmation.set($event)"
                      [attr.aria-label]="
                        'Type ' + impact.confirmation_key + ' to confirm metric deletion'
                      "
                      autocomplete="off"
                      autofocus
                    />
                  </label>
                }

                <div
                  class="flex flex-wrap justify-end gap-2 border-t border-[var(--t-border)] pt-4"
                >
                  <button
                    type="button"
                    class="btn-secondary px-4 py-2 text-[10px]"
                    (click)="closeMetricDeletion()"
                    aria-label="Cancel metric deletion"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    class="btn-secondary px-4 py-2 text-[10px]"
                    (click)="hideMetricInstead()"
                    [disabled]="saving()"
                    aria-label="Hide metric instead of deleting"
                  >
                    Hide instead
                  </button>
                  @if (impact.can_delete) {
                    <button
                      type="button"
                      class="btn-primary px-4 py-2 text-[10px] disabled:cursor-not-allowed disabled:opacity-40"
                      (click)="confirmMetricDeletion()"
                      [disabled]="
                        deletionConfirmation() !== impact.confirmation_key || deletionLoading()
                      "
                      [attr.aria-label]="'Permanently delete metric ' + metric.label"
                    >
                      Permanently delete
                    </button>
                  }
                </div>
              </div>
            }
          </section>
        </div>
      }
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .section-label,
      .field-label {
        color: var(--t-text-tertiary);
        font-size: 0.625rem;
        font-weight: 900;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .section-title {
        color: var(--t-text-primary);
        font-size: 1.125rem;
        font-weight: 900;
        margin-top: 0.25rem;
      }
      .config-panel {
        border: 1px solid var(--t-border);
        background: var(--t-surface);
        min-width: 0;
      }
      .panel-header {
        align-items: center;
        background: var(--t-surface-raised);
        border-bottom: 1px solid var(--t-border);
        display: flex;
        gap: 1rem;
        justify-content: space-between;
        padding: 1rem;
      }
    `,
  ],
})
export class FinancialConfigurationComponent implements OnInit, OnDestroy {
  private readonly facade = inject(FinancialConfigurationFacade);
  private readonly host: ElementRef<HTMLElement> = inject(ElementRef);
  private deletionTrigger: HTMLElement | null = null;
  private previousBodyOverflow = '';
  readonly tabs: Array<{ key: FinancialSubtab; label: string }> = [
    { key: 'settings', label: 'Settings' },
    { key: 'metrics', label: 'Metrics & formulas' },
    { key: 'planning', label: 'Baselines & scenarios' },
    { key: 'bridge', label: 'Value bridge' },
    { key: 'taxonomy', label: 'Taxonomy' },
  ];
  readonly fiscalMonths = Array.from({ length: 12 }, (_, index) => ({
    value: index + 1,
    label: new Date(2024, index, 1).toLocaleString('en', { month: 'long' }),
  }));
  readonly activeSubtab = signal<FinancialSubtab>('settings');
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly message = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  readonly settings = signal<FinancialReportingSettings>({ ...DEFAULT_SETTINGS });
  readonly metrics = signal<FinancialMetricDefinition[]>([]);
  readonly scenarios = signal<FinancialScenario[]>([]);
  readonly bridgeRows = signal<FinancialBridgeRow[]>([]);
  readonly costCategories = signal<FinancialCostCategory[]>([]);
  readonly attributes = signal<FinancialAttributeDefinition[]>([]);
  readonly selectedMetric = signal<FinancialMetricDefinition | null>(null);
  readonly selectedBridgeRow = signal<FinancialBridgeRow | null>(null);
  readonly metricSearch = signal('');
  readonly baselineYear = signal(new Date().getFullYear());
  readonly baselineValues = signal<Record<string, string>>({});
  readonly deletionMetric = signal<FinancialMetricDefinition | null>(null);
  readonly deletionImpact = signal<FinancialMetricDeletionImpact | null>(null);
  readonly deletionConfirmation = signal('');
  readonly deletionLoading = signal(false);

  ngOnInit(): void {
    this.load();
  }
  ngOnDestroy(): void {
    document.body.style.overflow = this.previousBodyOverflow;
  }
  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.facade
      .load()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.metrics.set(response.definitions || []);
          this.scenarios.set(response.scenarios || []);
          this.bridgeRows.set(response.bridge_rows || []);
          this.costCategories.set(response.cost_categories || []);
          this.attributes.set(response.attribute_definitions || []);
          this.settings.set({ ...DEFAULT_SETTINGS, ...(response.settings || {}) });
          this.selectedMetric.set(this.metrics()[0] || null);
          this.selectedBridgeRow.set(this.bridgeRows()[0] || null);
          this.loadBaselines();
        },
        error: (err) =>
          this.error.set(err.error?.detail || 'Could not load financial configuration.'),
      });
  }
  moveTab(index: number, direction: number): void {
    this.activeSubtab.set(this.tabs[(index + direction + this.tabs.length) % this.tabs.length].key);
  }
  patchSettings<K extends keyof FinancialReportingSettings>(
    key: K,
    value: FinancialReportingSettings[K],
  ): void {
    this.settings.update((current) => ({ ...current, [key]: value }));
  }
  saveSettings(): void {
    const currency = this.settings().reporting_currency.trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(currency)) {
      this.error.set('Enter a valid three-letter ISO reporting currency.');
      return;
    }
    this.runSave(
      this.facade.saveSettings({ ...this.settings(), reporting_currency: currency }),
      'Financial settings saved.',
    );
  }
  filteredMetrics(): FinancialMetricDefinition[] {
    const query = this.metricSearch().trim().toLowerCase();
    return this.metrics().filter(
      (row) => !query || `${row.label} ${row.key}`.toLowerCase().includes(query),
    );
  }
  addMetric(): void {
    const index = this.metrics().length + 1;
    const label = `Custom Metric ${index}`;
    const metric: FinancialMetricDefinition = {
      key: uniqueFinancialKey(
        label,
        'metric',
        this.metrics().map((row) => row.key),
      ),
      label,
      group_key: 'custom',
      value_type: 'currency',
      direction: 'increase_good',
      aggregation: 'sum',
      rollup_type: 'benefit',
      is_benefit: true,
      benefit_class: 'other',
      formula: null,
      formula_inputs: [],
      precision: 4,
      display_order: 1000 + index,
      applies_to: 'opt_in',
      validation: {},
      is_system: false,
      is_active: true,
    };
    this.metrics.update((rows) => [...rows, metric]);
    this.selectedMetric.set(metric);
  }
  updateMetricLabel(metric: FinancialMetricDefinition, label: string): void {
    metric.label = label;
    if (!metric.id && !metric.keyManuallyEdited)
      metric.key = uniqueFinancialKey(
        label,
        'metric',
        this.metrics()
          .filter((row) => row !== metric)
          .map((row) => row.key),
      );
  }
  updateMetricKey(metric: FinancialMetricDefinition, key: string): void {
    metric.key = key.trim().toLowerCase();
    metric.keyManuallyEdited = true;
  }
  metricKeyError(metric: FinancialMetricDefinition): string | null {
    return metric.id
      ? null
      : financialKeyError(
          metric.key,
          this.metrics()
            .filter((row) => row !== metric)
            .map((row) => row.key),
        );
  }
  updateBenefitClass(metric: FinancialMetricDefinition, value: string): void {
    metric.benefit_class = value || null;
    metric.is_benefit = Boolean(value);
    metric.rollup_type = value ? 'benefit' : null;
  }
  updateFormula(metric: FinancialMetricDefinition, formula: string): void {
    metric.formula = formula || null;
    metric.formula_inputs = formulaIdentifiers(formula);
  }
  availableFormulaVariables(
    metric: FinancialMetricDefinition,
  ): Array<{ key: string; label: string }> {
    return this.metrics()
      .filter((row) => row !== metric && row.is_active !== false)
      .flatMap((row) => [
        { key: row.key, label: row.label },
        { key: `baseline_${row.key}`, label: `Baseline · ${row.label}` },
      ]);
  }
  insertFormulaKey(
    metric: FinancialMetricDefinition,
    key: string,
    textarea: HTMLTextAreaElement,
  ): void {
    const start = textarea.selectionStart ?? String(metric.formula || '').length;
    const end = textarea.selectionEnd ?? start;
    const current = String(metric.formula || '');
    const prefix = start > 0 && !/\s|\($/.test(current.slice(0, start)) ? ' ' : '';
    const suffix = end < current.length && !/\s|\)/.test(current.slice(end)) ? ' ' : '';
    this.updateFormula(
      metric,
      `${current.slice(0, start)}${prefix}${key}${suffix}${current.slice(end)}`,
    );
    queueMicrotask(() => {
      const cursor = start + prefix.length + key.length + suffix.length;
      textarea.focus();
      textarea.setSelectionRange(cursor, cursor);
    });
  }
  saveMetric(metric: FinancialMetricDefinition): void {
    const keyError = this.metricKeyError(metric);
    if (keyError) {
      this.error.set(keyError);
      return;
    }
    this.runSave(this.facade.saveMetric(metric), 'Metric saved.', true);
  }
  discardMetric(metric: FinancialMetricDefinition): void {
    this.metrics.update((rows) => rows.filter((row) => row !== metric));
    this.selectedMetric.set(this.metrics()[0] || null);
    this.message.set('Unsaved metric discarded.');
  }
  openMetricDeletion(metric: FinancialMetricDefinition): void {
    if (!metric.id) return;
    this.deletionTrigger = document.activeElement as HTMLElement | null;
    this.previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    this.deletionMetric.set(metric);
    this.deletionImpact.set(null);
    this.deletionConfirmation.set('');
    this.deletionLoading.set(true);
    this.error.set(null);
    queueMicrotask(() =>
      this.host.nativeElement
        .querySelector<HTMLElement>('[data-testid="metric-deletion-dialog"]')
        ?.focus(),
    );
    this.facade
      .loadMetricDeletionImpact(metric.id)
      .pipe(finalize(() => this.deletionLoading.set(false)))
      .subscribe({
        next: (impact) => this.deletionImpact.set(impact),
        error: (err) => {
          this.closeMetricDeletion();
          this.error.set(err.error?.detail || 'Could not check metric dependencies.');
        },
      });
  }
  isDefaultMetric(metric: FinancialMetricDefinition): boolean {
    return (
      metric.origin === 'default_catalog' ||
      metric.origin === 'legacy_default' ||
      (!metric.origin && metric.is_system === true)
    );
  }
  defaultMetricExplanation(metric: FinancialMetricDefinition): string {
    if (metric.origin === 'legacy_default') {
      return 'This metric came from your tenant’s original starter catalogue.';
    }
    return metric.catalog_version
      ? `This metric came from recommended catalogue ${metric.catalog_version}.`
      : 'This metric came from the recommended starter catalogue.';
  }
  closeMetricDeletion(): void {
    document.body.style.overflow = this.previousBodyOverflow;
    this.deletionMetric.set(null);
    this.deletionImpact.set(null);
    this.deletionConfirmation.set('');
    const trigger = this.deletionTrigger;
    this.deletionTrigger = null;
    queueMicrotask(() => trigger?.focus());
  }
  trapDeletionFocus(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;
    const dialog = this.host.nativeElement.querySelector<HTMLElement>(
      '[data-testid="metric-deletion-dialog"]',
    );
    if (!dialog) return;
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])'),
    );
    if (!focusable.length) {
      keyboardEvent.preventDefault();
      dialog.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (keyboardEvent.shiftKey && document.activeElement === first) {
      keyboardEvent.preventDefault();
      last.focus();
    } else if (!keyboardEvent.shiftKey && document.activeElement === last) {
      keyboardEvent.preventDefault();
      first.focus();
    }
  }
  deletionBlockers(): Array<{
    key: string;
    label: string;
    category: FinancialMetricDeletionCategory;
  }> {
    const impact = this.deletionImpact();
    if (!impact) return [];
    const labels: Record<string, string> = {
      benefit_lines: 'Benefit lines',
      metric_values: 'Metric values',
      initiative_scope: 'Initiative scope',
      initiative_baselines: 'Initiative baselines',
      legacy_selections: 'Legacy selections',
      legacy_configuration: 'Legacy configuration',
      formula_dependencies: 'Formula dependencies',
      bridge_rows: 'Value bridge rows',
      shared_cost_rules: 'Shared-cost rules',
      shared_cost_allocations: 'Historical allocations',
    };
    return Object.entries(impact.blockers)
      .filter(([, category]) => category.count > 0)
      .map(([key, category]) => ({ key, label: labels[key] || key, category }));
  }
  hideMetricInstead(): void {
    const metric = this.deletionMetric();
    if (!metric) return;
    metric.is_active = false;
    this.closeMetricDeletion();
    this.saveMetric(metric);
  }
  confirmMetricDeletion(): void {
    const metric = this.deletionMetric();
    const impact = this.deletionImpact();
    if (
      !metric?.id ||
      !impact?.can_delete ||
      this.deletionConfirmation() !== impact.confirmation_key
    )
      return;
    this.deletionLoading.set(true);
    this.error.set(null);
    this.facade
      .deleteMetric(metric.id, this.deletionConfirmation())
      .pipe(finalize(() => this.deletionLoading.set(false)))
      .subscribe({
        next: () => {
          this.closeMetricDeletion();
          this.message.set(`Metric ${metric.label} deleted.`);
          this.load();
        },
        error: (err) => {
          const detail = err.error?.detail;
          if (detail?.impact) this.deletionImpact.set(detail.impact);
          this.error.set(
            typeof detail === 'string'
              ? detail
              : detail?.message || 'Could not delete the financial metric.',
          );
        },
      });
  }
  copyKey(key: string): void {
    navigator.clipboard
      .writeText(key)
      .then(() => this.message.set(`Copied ${key}.`))
      .catch(() => this.error.set('Could not copy the key. Select it and copy manually.'));
  }

  addScenario(): void {
    const index = this.scenarios().length + 1;
    const label = `Scenario ${index}`;
    this.scenarios.update((rows) => [
      ...rows,
      {
        key: uniqueFinancialKey(
          label,
          'scenario',
          rows.map((row) => row.key),
        ),
        label,
        kind: 'plan',
        is_primary: false,
        is_system: false,
        is_active: true,
        display_order: 1000 + index,
      },
    ]);
  }
  saveScenario(row: FinancialScenario): void {
    this.runSave(this.facade.saveScenario(row), 'Scenario saved.', true);
  }
  loadBaselines(): void {
    this.facade.loadAnnualBaselines().subscribe({
      next: (response) => {
        const values: Record<string, string> = {};
        for (const row of response.values || [])
          if (Number(row.baseline_year) === this.baselineYear())
            values[row.metric_definition_id] = row.value;
        this.baselineValues.set(values);
      },
      error: () => this.baselineValues.set({}),
    });
  }
  baselineMetrics(): FinancialMetricDefinition[] {
    return this.metrics()
      .filter((row) => row.id && row.is_active !== false && row.aggregation !== 'formula')
      .sort((a, b) => a.display_order - b.display_order || a.label.localeCompare(b.label));
  }
  setBaselineYear(value: string | number): void {
    this.baselineYear.set(this.numberValue(value));
    this.loadBaselines();
  }
  setBaselineValue(id: string, value: string | number): void {
    this.baselineValues.update((current) => ({ ...current, [id]: String(value ?? '') }));
  }
  saveBaselines(): void {
    const values = Object.entries(this.baselineValues())
      .filter(([, value]) => value.trim() !== '')
      .map(([metric_definition_id, value]) => ({
        metric_definition_id,
        baseline_year: this.baselineYear(),
        value,
      }));
    this.runSave(this.facade.saveAnnualBaselines(values), 'Annual baselines saved.');
  }

  addBridgeRow(): void {
    const index = this.bridgeRows().length + 1;
    const label = `Bridge Row ${index}`;
    const row: FinancialBridgeRow = {
      key: uniqueFinancialKey(
        label,
        'bridge_row',
        this.bridgeRows().map((item) => item.key),
      ),
      label,
      row_kind: 'metric_set',
      metric_definition_ids: [],
      cost_category_ids: [],
      cost_category_keys: [],
      sign: 1,
      display_order: 1000 + index,
      is_active: true,
    };
    this.bridgeRows.update((rows) => [...rows, row]);
    this.selectedBridgeRow.set(row);
  }
  updateBridgeLabel(row: FinancialBridgeRow, label: string): void {
    row.label = label;
    if (!row.id && !row.keyManuallyEdited)
      row.key = uniqueFinancialKey(
        label,
        'bridge_row',
        this.bridgeRows()
          .filter((item) => item !== row)
          .map((item) => item.key),
      );
  }
  updateBridgeKey(row: FinancialBridgeRow, key: string): void {
    row.key = key.trim().toLowerCase();
    row.keyManuallyEdited = true;
  }
  bridgeKeyError(row: FinancialBridgeRow): string | null {
    return row.id
      ? null
      : financialKeyError(
          row.key,
          this.bridgeRows()
            .filter((item) => item !== row)
            .map((item) => item.key),
        );
  }
  normalizeBridgeRow(row: FinancialBridgeRow): void {
    if (row.row_kind === 'net') {
      row.metric_definition_ids = [];
      row.cost_category_ids = [];
      row.cost_category_keys = [];
    }
  }
  bridgeKindLabel(kind: FinancialBridgeRow['row_kind']): string {
    return { metric_set: 'Metrics', cost_set: 'Costs', subtotal: 'Subtotal', net: 'Net' }[kind];
  }
  bridgeInputCount(row: FinancialBridgeRow): number {
    return row.metric_definition_ids.length + row.cost_category_ids.length;
  }
  toggleMetric(row: FinancialBridgeRow, id: string): void {
    row.metric_definition_ids = row.metric_definition_ids.includes(id)
      ? row.metric_definition_ids.filter((value) => value !== id)
      : [...row.metric_definition_ids, id];
  }
  toggleCostCategory(row: FinancialBridgeRow, id: string): void {
    row.cost_category_ids = row.cost_category_ids.includes(id)
      ? row.cost_category_ids.filter((value) => value !== id)
      : [...row.cost_category_ids, id];
  }
  saveBridgeRow(row: FinancialBridgeRow): void {
    const keyError = this.bridgeKeyError(row);
    if (keyError) {
      this.error.set(keyError);
      return;
    }
    this.normalizeBridgeRow(row);
    this.runSave(this.facade.saveBridgeRow(row), 'Value bridge row saved.', true);
  }

  activeCostCategories(): FinancialCostCategory[] {
    return this.costCategories()
      .filter((row) => row.id && row.is_active !== false)
      .sort((a, b) => a.display_order - b.display_order || a.label.localeCompare(b.label));
  }
  addCostCategory(): void {
    const index = this.costCategories().length + 1;
    const label = `Cost Category ${index}`;
    this.costCategories.update((rows) => [
      ...rows,
      {
        key: uniqueFinancialKey(
          label,
          'cost_category',
          rows.map((row) => row.key),
        ),
        label,
        group_key: 'costs',
        rollup_type: 'one_off_cost',
        display_order: 1000 + index,
        attributes: {},
        is_system: false,
        is_active: true,
      },
    ]);
  }
  saveCostCategory(row: FinancialCostCategory): void {
    this.runSave(this.facade.saveCostCategory(row), 'Cost category saved.', true);
  }
  addAttribute(): void {
    const index = this.attributes().length + 1;
    const label = `Line Attribute ${index}`;
    this.attributes.update((rows) => [
      ...rows,
      {
        key: uniqueFinancialKey(
          label,
          'attribute',
          rows.map((row) => row.key),
        ),
        label,
        entity_type: 'benefit_line',
        value_type: 'text',
        options: [],
        is_required: false,
        display_order: 1000 + index,
        is_active: true,
      },
    ]);
  }
  setAttributeOptions(row: FinancialAttributeDefinition, value: string): void {
    row.options = [
      ...new Set(
        String(value || '')
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    ];
  }
  saveAttribute(row: FinancialAttributeDefinition): void {
    this.runSave(this.facade.saveAttribute(row), 'Line attribute saved.', true);
  }
  numberValue(value: string | number): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private runSave(
    request: ReturnType<FinancialConfigurationFacade['saveAnnualBaselines']>,
    success: string,
    reload = false,
  ): void {
    this.saving.set(true);
    this.message.set(null);
    this.error.set(null);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.message.set(success);
        if (reload) this.load();
      },
      error: (err) =>
        this.error.set(err.error?.detail || 'Could not save the financial configuration.'),
    });
  }
}
