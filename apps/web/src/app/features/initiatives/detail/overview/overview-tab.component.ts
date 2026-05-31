import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ValueWaterfallComponent } from '../../../../shared/components/value-waterfall/value-waterfall.component';

interface FinancialSummary {
  revenue_uplift_plan_base: string;
  revenue_uplift_plan_high: string;
  revenue_uplift_actual: string | null;
  gross_margin_plan_base: string;
  gross_margin_plan_high: string;
  gross_margin_actual: string | null;
  gm_pct_plan_base: string;
  gm_pct_plan_high: string;
  gm_pct_actual: string | null;
  gm_uplift_plan_base: string;
  gm_uplift_plan_high: string;
  gm_uplift_actual: string | null;
  costs_recurring_plan: string;
  costs_recurring_actual: string | null;
  costs_one_off_plan: string;
  costs_one_off_actual: string | null;
  costs_plan: string;
  costs_actual: string | null;
  net_value_plan: string;
  net_value_actual: string | null;
  benefit_run_rate: string;
  cost_run_rate: string;
}

interface InitiativeFinancialSelections {
  metric_keys: string[];
  cost_category_keys: string[];
}

interface FinancialGrid {
  summary: FinancialSummary;
  selections?: InitiativeFinancialSelections;
}

interface PressureBreakdown {
  schedule: string | null;
  milestone_health: string | null;
  risk_exposure: string | null;
  kpi_performance: string | null;
  financial: string | null;
  self_reported: string | null;
}

interface InitiativeCounts {
  milestones_total: number;
  milestones_complete: number;
  milestones_overdue: number;
  kpis_total: number;
  risks_open: number;
  risks_high: number;
  status_updates_total: number;
}

interface InitiativeDetail {
  id: string;
  initiative_code: string;
  name: string;
  workstream_id: string | null;
  workstream_name: string | null;
  business_unit_id: string | null;
  business_unit_name: string | null;
  owner_name: string | null;
  group_owner_name: string | null;
  type: string | null;
  impact_type: string | null;
  theme: string | null;
  country: string | null;
  tag: string | null;
  priority: string;
  rag_status: string;
  stage: string;
  summary: string | null;
  dependencies_text: string | null;
  value_logic: string | null;
  planned_start: string | null;
  actual_start: string | null;
  planned_end: string | null;
  actual_end: string | null;
  pressure_score: string | null;
  pressure_breakdown: PressureBreakdown | null;
  counts: InitiativeCounts;
  financial_summary: FinancialSummary | null;
  team_members: Array<{
    id: string;
    user_id: string;
    role: string;
    display_name: string | null;
    email: string | null;
  }>;
  kpi_indicators: Array<{
    id: string;
    name: string;
    unit: string | null;
    health_status: string;
    this_quarter_actual: string | null;
    this_year_actual: string | null;
    all_time_actual: string | null;
  }>;
}

interface WorkstreamOption {
  id: string;
  name: string;
  business_unit_id: string | null;
}

interface BusinessUnitOption {
  id: string;
  name: string;
}

@Component({
  selector: 'app-overview-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, ValueWaterfallComponent],
  template: `
    <div class="space-y-6">
      <!-- Loading State -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 animate-pulse">
          <div class="card h-24 bg-[var(--t-surface-raised)]"></div>
          <div class="card h-24 bg-[var(--t-surface-raised)]"></div>
          <div class="card h-24 bg-[var(--t-surface-raised)]"></div>
          <div class="card h-24 bg-[var(--t-surface-raised)]"></div>
        </div>
      }

      @if (!loading() && detail()) {
        <!-- HEADER CONTEXT -->
        <div class="card p-5">
          <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2 mb-3">
                <span class="text-[10px] font-mono font-bold px-2 py-1 rounded-lg border"
                      style="color:var(--t-text-secondary);border-color:var(--t-border);background:var(--t-surface-raised)">
                  {{ detail()!.initiative_code }}
                </span>
                <span class="text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-lg"
                      [style.background]="statusBg(detail()!.stage)"
                      [style.color]="statusFg(detail()!.stage)">
                  {{ labelize(detail()!.stage) }}
                </span>
                <span class="text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-lg"
                      [style.background]="ragBg(detail()!.rag_status)"
                      [style.color]="ragFg(detail()!.rag_status)">
                  {{ detail()!.rag_status }}
                </span>
                <span class="text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-lg"
                      style="color:var(--t-accent);background:var(--t-accent-soft)">
                  {{ detail()!.priority }} priority
                </span>
              </div>
              <h2 class="text-2xl font-black tracking-tight truncate" style="color:var(--t-text-primary)">
                {{ detail()!.name }}
              </h2>
              <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs" style="color:var(--t-text-secondary)">
                <span><strong style="color:var(--t-text-primary)">BU:</strong> {{ detail()!.business_unit_name || 'Unassigned' }}</span>
                <span><strong style="color:var(--t-text-primary)">Workstream:</strong> {{ detail()!.workstream_name || 'Unassigned' }}</span>
                <span><strong style="color:var(--t-text-primary)">Market:</strong> {{ detail()!.country || 'N/A' }}</span>
                <span><strong style="color:var(--t-text-primary)">Theme:</strong> {{ detail()!.theme || 'N/A' }}</span>
                <span><strong style="color:var(--t-text-primary)">Tag:</strong> {{ labelize(detail()!.tag || '') || 'N/A' }}</span>
              </div>
            </div>
            <button (click)="openEditModal()" class="btn-secondary text-sm flex items-center gap-2" aria-label="Edit initiative overview">
              <span class="material-icons text-sm">edit</span>
              Edit Overview
            </button>
          </div>
        </div>

        <!-- TOP SUMMARY CARDS -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          @for (card of summaryCards(); track card.label) {
            <div class="card p-4 transition-all hover:border-[var(--t-accent)]">
              <p class="text-[10px] font-bold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">{{ card.label }}</p>
              
              <div class="space-y-3">
                <div>
                  <p class="text-[9px] uppercase font-semibold" style="color:var(--t-text-secondary)">Plan (Range)</p>
                  <p class="text-sm font-bold" [style.color]="card.highlight ? 'var(--t-accent)' : 'var(--t-text-primary)'">
                    {{ card.plan }}
                  </p>
                </div>
                <div class="pt-2 border-t" style="border-color:var(--t-border)">
                  <p class="text-[9px] uppercase font-semibold" style="color:var(--t-text-secondary)">Actual to Date</p>
                  <p class="text-sm font-bold" style="color:var(--t-text-primary)">
                    {{ card.actual }}
                  </p>
                </div>
              </div>
            </div>
          }
        </div>

        <!-- MAIN SECTION: Executive Summary & Context -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          <!-- Description Card & Waterfall -->
          <div class="lg:col-span-2 space-y-6">
            <div class="card relative">
              <button (click)="openEditModal()" class="absolute top-4 right-4 btn-ghost p-1 text-[var(--t-text-secondary)] hover:text-[var(--t-primary)]" aria-label="Edit executive summary">
                <span class="material-icons text-sm">edit</span>
              </button>
              <h3 class="text-sm font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Executive Summary
              </h3>
              <p class="text-sm leading-relaxed" style="color:var(--t-text-primary)">
                {{ detail()!.summary || 'No summary provided.' }}
              </p>
              @if (detail()!.value_logic) {
                <div class="mt-6 pt-6 border-t" style="border-color:var(--t-border)">
                  <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">
                    Value Logic & Assumptions
                  </h4>
                  <p class="text-sm italic" style="color:var(--t-text-secondary)">
                    "{{ detail()!.value_logic }}"
                  </p>
                </div>
              }
              @if (detail()!.dependencies_text) {
                <div class="mt-6 pt-6 border-t" style="border-color:var(--t-border)">
                  <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">
                    Context & Dependencies
                  </h4>
                  <p class="text-sm" style="color:var(--t-text-secondary)">
                    {{ detail()!.dependencies_text }}
                  </p>
                </div>
              }
            </div>

            <!-- Value Bridge Waterfall -->
            <app-value-waterfall [data]="valueBridge()"></app-value-waterfall>

            <div class="card">
              <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                KPI Indicators
              </h3>
              @if (detail()!.kpi_indicators.length > 0) {
                <div class="overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead>
                      <tr class="text-[10px] uppercase tracking-wider" style="color:var(--t-text-secondary)">
                        <th class="text-left py-2 font-bold">KPI</th>
                        <th class="text-right py-2 font-bold">This Quarter</th>
                        <th class="text-right py-2 font-bold">This Year</th>
                        <th class="text-right py-2 font-bold">All Time</th>
                        <th class="text-right py-2 font-bold">Health</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (kpi of detail()!.kpi_indicators; track kpi.id) {
                        <tr class="border-t" style="border-color:var(--t-border)">
                          <td class="py-3 font-bold" style="color:var(--t-text-primary)">{{ kpi.name }}</td>
                          <td class="py-3 text-right font-mono" style="color:var(--t-text-secondary)">{{ formatKpi(kpi.this_quarter_actual, kpi.unit) }}</td>
                          <td class="py-3 text-right font-mono" style="color:var(--t-text-secondary)">{{ formatKpi(kpi.this_year_actual, kpi.unit) }}</td>
                          <td class="py-3 text-right font-mono" style="color:var(--t-text-primary)">{{ formatKpi(kpi.all_time_actual, kpi.unit) }}</td>
                          <td class="py-3 text-right">
                            <span class="text-[9px] uppercase font-black px-2 py-1 rounded"
                                  [style.color]="healthFg(kpi.health_status)"
                                  [style.background]="healthBg(kpi.health_status)">
                              {{ labelize(kpi.health_status) }}
                            </span>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else {
                <p class="text-sm" style="color:var(--t-text-secondary)">No KPI indicators configured yet.</p>
              }
            </div>
          </div>


          <!-- SIDEBAR: Timeline & Pressure -->
          <div class="space-y-6">
            <!-- Timeline Card -->
            <div class="card">
              <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Timeline
              </h3>
              <div class="space-y-4">
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Start</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.planned_start || '—' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Completion</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.planned_end || '—' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Actual Start</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.actual_start || '—' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Actual End</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.actual_end || '—' }}</span>
                </div>
                <!-- Progress Bar -->
                <div class="pt-2">
                  <div class="flex justify-between text-[10px] mb-1">
                    <span style="color:var(--t-text-secondary)">Overall Progress</span>
                    <span class="font-bold" style="color:var(--t-accent)">{{ progressPct() }}%</span>
                  </div>
                  <div class="h-2 rounded-full" style="background:var(--t-surface-raised)">
                    <div class="h-full rounded-full transition-all duration-500"
                         [style.width]="progressPct() + '%'"
                         style="background:var(--t-accent-gradient)"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Pressure Card -->
            <div class="card">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-xs font-semibold uppercase tracking-wider" style="color:var(--t-text-secondary)">
                  Value Pressure
                </h3>
                <span class="text-xl font-bold" [style.color]="pressureColor(detail()!.pressure_score)">
                  {{ detail()!.pressure_score || '0.0' }}
                </span>
              </div>
              <div class="space-y-3">
                @for (p of pressureGauges(); track p.label) {
                  <div>
                    <div class="flex justify-between text-[10px] mb-1">
                      <span style="color:var(--t-text-secondary)">{{ p.label }}</span>
                      <span class="font-mono" style="color:var(--t-text-primary)">{{ p.value }}/10</span>
                    </div>
                    <div class="h-1 rounded-full overflow-hidden" style="background:var(--t-surface-raised)">
                      <div class="h-full rounded-full transition-all duration-500"
                           [style.width]="(p.value * 10) + '%'"
                           [style.background]="pressureColor(p.value)"></div>
                    </div>
                  </div>
                }
              </div>
            </div>

            <!-- Financial Sidebar -->
            <div class="card">
              <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Financial Summary
              </h3>
              <div class="space-y-3">
                @for (row of financialSidebar(); track row.label) {
                  <div class="flex items-center justify-between text-sm">
                    <span style="color:var(--t-text-secondary)">{{ row.label }}</span>
                    <span class="font-bold" style="color:var(--t-text-primary)">{{ row.value }}</span>
                  </div>
                }
              </div>
            </div>

            <!-- Team Quick View -->
            <div class="card">
               <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Lead Team
              </h3>
              <div class="space-y-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] font-bold text-xs">
                    {{ getInitials(detail()!.owner_name) }}
                  </div>
                  <div>
                    <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ detail()!.owner_name || 'Unassigned' }}</p>
                    <p class="text-[10px]" style="color:var(--t-text-secondary)">Market Owner</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-secondary)] font-bold text-xs">
                    {{ getInitials(detail()!.group_owner_name) }}
                  </div>
                  <div>
                    <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ detail()!.group_owner_name || 'Unassigned' }}</p>
                    <p class="text-[10px]" style="color:var(--t-text-secondary)">Group Owner</p>
                  </div>
                </div>
                @for (member of detail()!.team_members.slice(0, 3); track member.id) {
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-secondary)] font-bold text-xs">
                      {{ getInitials(member.display_name) }}
                    </div>
                    <div>
                      <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ member.display_name || 'Team member' }}</p>
                      <p class="text-[10px] capitalize" style="color:var(--t-text-secondary)">{{ member.role }}</p>
                    </div>
                  </div>
                }
                <div class="flex items-center gap-3 pt-2 border-t" style="border-color:var(--t-border)">
                  <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-secondary)] font-bold text-xs">
                    {{ getInitials(detail()!.workstream_name) }}
                  </div>
                  <div>
                    <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ detail()!.workstream_name || 'N/A' }}</p>
                    <p class="text-[10px]" style="color:var(--t-text-secondary)">Workstream</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      }

      <!-- Edit Modal -->
      @if (isEditing()) {
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div class="bg-[var(--t-surface)] border border-[var(--t-border)] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div class="px-6 py-4 border-b border-[var(--t-border)] flex justify-between items-center">
              <h2 class="text-lg font-bold text-[var(--t-text-primary)]">Edit Initiative Details</h2>
              <button (click)="closeEditModal()" class="text-[var(--t-text-secondary)] hover:text-[var(--t-text-primary)]">
                <span class="material-icons">close</span>
              </button>
            </div>
            <div class="p-6 overflow-y-auto space-y-4">
              <div>
                <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Name</label>
                <input type="text" [(ngModel)]="editData.name" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Business Unit</label>
                  <select [(ngModel)]="editData.business_unit_id" (ngModelChange)="onEditBusinessUnitChange($event)" aria-label="Initiative business unit" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="">Select business unit</option>
                    @for (bu of businessUnits(); track bu.id) {
                      <option [value]="bu.id">{{ bu.name }}</option>
                    }
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Workstream</label>
                  <select [(ngModel)]="editData.workstream_id" (ngModelChange)="onEditWorkstreamChange($event)" aria-label="Initiative workstream" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="">Select workstream</option>
                    @for (ws of filteredWorkstreams(); track ws.id) {
                      <option [value]="ws.id">{{ ws.name }}</option>
                    }
                  </select>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Market</label>
                  <select [(ngModel)]="editData.country" aria-label="Initiative market" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="">Select market</option>
                    @for (market of marketOptions(); track market) {
                      <option [value]="market">{{ market }}</option>
                    }
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Theme</label>
                  <select [(ngModel)]="editData.theme" aria-label="Initiative theme" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="">Select theme</option>
                    @for (theme of themeOptions(); track theme) {
                      <option [value]="theme">{{ theme }}</option>
                    }
                  </select>
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Tag</label>
                <select [(ngModel)]="editData.tag" aria-label="Initiative tag" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                  <option value="">Select tag</option>
                  @for (tag of tagOptions(); track tag) {
                    <option [value]="tag">{{ labelize(tag) }}</option>
                  }
                </select>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Stage</label>
                  <select [(ngModel)]="editData.stage" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="scoping">Scoping</option>
                    <option value="in_progress">In Progress</option>
                    <option value="complete">Complete</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">RAG Status</label>
                  <select [(ngModel)]="editData.rag_status" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                    <option value="green">Green</option>
                    <option value="amber">Amber</option>
                    <option value="red">Red</option>
                  </select>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Planned Start</label>
                  <input type="date" [(ngModel)]="editData.planned_start" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                </div>
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Planned End</label>
                  <input type="date" [(ngModel)]="editData.planned_end" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Actual Start</label>
                  <input type="date" [(ngModel)]="editData.actual_start" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                </div>
                <div>
                  <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Actual End</label>
                  <input type="date" [(ngModel)]="editData.actual_end" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none">
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Description (Summary)</label>
                <textarea [(ngModel)]="editData.summary" rows="4" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none"></textarea>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Value Logic</label>
                <textarea [(ngModel)]="editData.value_logic" rows="3" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none"></textarea>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase text-[var(--t-text-secondary)] mb-1">Context & Dependencies</label>
                <textarea [(ngModel)]="editData.dependencies_text" rows="3" class="w-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-3 py-2 text-sm text-[var(--t-text-primary)] focus:border-[var(--t-primary)] outline-none"></textarea>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-[var(--t-border)] flex justify-end gap-3 bg-[var(--t-surface-raised)]">
              <button (click)="closeEditModal()" class="btn-ghost px-4 py-2 text-sm font-medium">Cancel</button>
              <button (click)="saveInitiative()" class="btn-primary flex items-center gap-2 px-4 py-2 text-sm font-medium" [disabled]="saving()">
                @if (saving()) {
                  <span class="material-icons animate-spin text-sm">sync</span> Saving...
                } @else {
                  Save Changes
                }
              </button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .card {
      @apply rounded-xl border p-5 shadow-sm bg-[var(--t-surface)] transition-all duration-200;
      border-color: var(--t-border);
    }
  `]
})
export class OverviewTabComponent implements OnInit {
  @Input() initiativeId = '';

  private readonly api = inject(ApiService);

  loading = signal(true);
  detail = signal<InitiativeDetail | null>(null);
  grid = signal<FinancialGrid | null>(null);
  valueBridge = signal<any | null>(null);
  workstreams = signal<WorkstreamOption[]>([]);
  businessUnits = signal<BusinessUnitOption[]>([]);
  markets = signal<string[]>([]);
  themes = signal<string[]>([]);
  tags = signal<string[]>([]);

  isEditing = signal(false);
  saving = signal(false);
  editData: any = {};
  private readonly defaultTags = ['automation', 'offshoring', 'commercial', 'other'];
  private readonly defaultMetricKeys = [
    'revenue_uplift_base',
    'revenue_uplift_high',
    'revenue_uplift_actual',
    'gm_uplift_base',
    'gm_uplift_high',
    'gm_uplift_actual',
  ];
  private readonly defaultCostCategoryKeys = ['implementation', 'maintenance'];

  summaryCards = computed(() => {
    const s = this.grid()?.summary;
    if (!s) return [];
    
    const gmRange = `${this.formatMoney(s.gm_uplift_plan_base)} - ${this.formatMoney(s.gm_uplift_plan_high)}`;
    const revRange = `${this.formatMoney(s.revenue_uplift_plan_base)} - ${this.formatMoney(s.revenue_uplift_plan_high)}`;

    const cards: Array<{ label: string; plan: string; actual: string; highlight: boolean }> = [];
    if (this.hasSelectedMetric(['revenue_uplift_base', 'revenue_uplift_high', 'revenue_uplift_actual'])) {
      cards.push({ label: 'Revenue Uplift', plan: revRange, actual: s.revenue_uplift_actual ? this.formatMoney(s.revenue_uplift_actual) : '—', highlight: false });
    }
    if (this.hasSelectedMetric(['gm_uplift_base', 'gm_uplift_high', 'gm_uplift_actual'])) {
      cards.push({ label: 'GM Uplift', plan: gmRange, actual: s.gm_uplift_actual ? this.formatMoney(s.gm_uplift_actual) : '—', highlight: false });
    }
    if (this.hasSelectedCosts()) {
      cards.push({ label: 'Total Costs', plan: this.formatMoney(s.costs_plan), actual: s.costs_actual ? this.formatMoney(s.costs_actual) : '—', highlight: false });
    }
    cards.push({ label: 'Net Value', plan: this.formatMoney(s.net_value_plan), actual: s.net_value_actual ? this.formatMoney(s.net_value_actual) : '—', highlight: true });
    return cards;
  });

  financialSidebar = computed(() => {
    const s = this.grid()?.summary;
    if (!s) return [];
    const rows = [
      { label: 'Initiative Value', value: this.formatMoney(s.net_value_plan) },
    ];
    if (this.hasSelectedMetric(['revenue_uplift_base', 'revenue_uplift_high', 'revenue_uplift_actual', 'gm_uplift_base', 'gm_uplift_high', 'gm_uplift_actual'])) {
      rows.push({ label: 'Benefit Run Rate', value: this.formatMoney(s.benefit_run_rate) });
    }
    if (this.hasSelectedCosts()) {
      rows.push({ label: 'Cost Run Rate', value: this.formatMoney(s.cost_run_rate) });
      rows.push({ label: 'One-off Costs', value: this.formatMoney(s.costs_one_off_plan) });
    }
    return rows;
  });

  private selectedMetricKeySet(): Set<string> {
    const selections = this.grid()?.selections;
    return new Set(selections ? selections.metric_keys : this.defaultMetricKeys);
  }

  private selectedCostCategoryKeySet(): Set<string> {
    const selections = this.grid()?.selections;
    return new Set(selections ? selections.cost_category_keys : this.defaultCostCategoryKeys);
  }

  private hasSelectedMetric(keys: string[]): boolean {
    const selected = this.selectedMetricKeySet();
    return keys.some(key => selected.has(key));
  }

  private hasSelectedCosts(): boolean {
    return this.selectedCostCategoryKeySet().size > 0;
  }

  pressureGauges = computed(() => {
    const b = this.detail()?.pressure_breakdown;
    if (!b) return [];
    return [
      { label: 'Schedule', value: parseFloat(b.schedule || '0') },
      { label: 'Milestones', value: parseFloat(b.milestone_health || '0') },
      { label: 'Financials', value: parseFloat(b.financial || '0') },
      { label: 'Risks', value: parseFloat(b.risk_exposure || '0') },
    ];
  });

  progressPct = computed(() => {
    const c = this.detail()?.counts;
    if (!c || c.milestones_total === 0) return 0;
    return Math.round((c.milestones_complete / c.milestones_total) * 100);
  });

  ngOnInit(): void {
    if (!this.initiativeId) return;
    this.loadDropdownData();
    this.loadDetail();
    this.api.get<FinancialGrid>(`/initiatives/${this.initiativeId}/financials`).subscribe(g => this.grid.set(g));
    this.api.get<any>(`/initiatives/${this.initiativeId}/financials/value-bridge`).subscribe(vb => this.valueBridge.set(vb));
  }

  private loadDetail(): void {
    this.loading.set(true);
    this.api.get<InitiativeDetail>(`/initiatives/${this.initiativeId}`).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openEditModal(): void {
    const d = this.detail();
    if (!d) return;
    this.editData = {
      name: d.name,
      business_unit_id: d.business_unit_id || '',
      workstream_id: d.workstream_id || '',
      country: d.country || '',
      theme: d.theme || '',
      tag: d.tag || '',
      stage: d.stage,
      rag_status: d.rag_status,
      summary: d.summary,
      value_logic: d.value_logic,
      dependencies_text: d.dependencies_text,
      planned_start: d.planned_start,
      planned_end: d.planned_end,
      actual_start: d.actual_start,
      actual_end: d.actual_end
    };
    this.isEditing.set(true);
  }

  closeEditModal(): void {
    this.isEditing.set(false);
  }

  saveInitiative(): void {
    this.saving.set(true);
    const payload = {
      ...this.editData,
      workstream_id: this.editData.workstream_id || null,
      country: this.editData.country || null,
      theme: this.editData.theme || null,
      tag: this.editData.tag || null,
    };
    delete payload.business_unit_id;
    this.api.put(`/initiatives/${this.initiativeId}`, payload).subscribe({
      next: (d) => {
        this.detail.set(d as any);
        this.saving.set(false);
        this.isEditing.set(false);
        // Refresh grid data if dates changed to keep summary cards consistent
        this.api.get<any>(`/initiatives/${this.initiativeId}/financials`).subscribe(g => this.grid.set(g));
      },
      error: () => {
        alert('Failed to save initiative details.');
        this.saving.set(false);
      }
    });
  }

  private loadDropdownData(): void {
    this.api.get<{ data?: WorkstreamOption[]; items?: WorkstreamOption[] }>('/workstreams').subscribe({
      next: r => this.workstreams.set(r.data ?? r.items ?? []),
      error: () => {},
    });
    this.api.get<{ data?: BusinessUnitOption[]; items?: BusinessUnitOption[] }>('/business-units').subscribe({
      next: r => this.businessUnits.set(r.data ?? r.items ?? []),
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
  }

  filteredWorkstreams(): WorkstreamOption[] {
    const businessUnitId = this.editData.business_unit_id;
    if (!businessUnitId) return this.workstreams();
    return this.workstreams().filter(ws => ws.business_unit_id === businessUnitId);
  }

  marketOptions(): string[] {
    return this.withCurrentOption(this.markets(), this.editData.country || '');
  }

  themeOptions(): string[] {
    return this.withCurrentOption(this.themes(), this.editData.theme || '');
  }

  tagOptions(): string[] {
    return this.withCurrentOption(this.tags(), this.editData.tag || '');
  }

  onEditBusinessUnitChange(businessUnitId: string): void {
    this.editData.business_unit_id = businessUnitId;
    if (!businessUnitId) return;
    const selectedWorkstream = this.workstreams().find(ws => ws.id === this.editData.workstream_id);
    if (selectedWorkstream && selectedWorkstream.business_unit_id !== businessUnitId) {
      this.editData.workstream_id = '';
    }
  }

  onEditWorkstreamChange(workstreamId: string): void {
    this.editData.workstream_id = workstreamId;
    const selectedWorkstream = this.workstreams().find(ws => ws.id === workstreamId);
    if (selectedWorkstream?.business_unit_id) {
      this.editData.business_unit_id = selectedWorkstream.business_unit_id;
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

  formatMoney(val: string | null | undefined): string {
    if (!val) return '$0';
    const n = parseFloat(val);
    if (isNaN(n)) return '$0';
    if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
    if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
    return `$${n.toLocaleString()}`;
  }

  formatKpi(val: string | null | undefined, unit: string | null | undefined): string {
    if (!val) return '—';
    const n = parseFloat(val);
    const formatted = Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : val;
    if (!unit) return formatted;
    if (unit === '%' || unit === 'x') return `${formatted}${unit}`;
    if (unit.toUpperCase() === 'USD' || unit === '$') return this.formatMoney(val);
    return `${formatted} ${unit}`;
  }

  pressureColor(score: string | number | null | undefined): string {
    if (!score) return 'var(--t-text-secondary)';
    const n = typeof score === 'string' ? parseFloat(score) : score;
    if (n >= 7) return 'var(--t-red)';
    if (n >= 4) return 'var(--t-amber)';
    return 'var(--t-green)';
  }

  getInitials(name: string | null | undefined): string {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  }

  labelize(value: string | null | undefined): string {
    return (value || 'n/a').replace(/_/g, ' ');
  }

  statusBg(value: string): string {
    return value === 'complete' ? 'rgba(16,185,129,0.12)'
         : value === 'in_progress' ? 'rgba(124,58,237,0.12)'
         : 'var(--t-surface-raised)';
  }

  statusFg(value: string): string {
    return value === 'complete' ? 'var(--t-green)'
         : value === 'in_progress' ? 'var(--t-accent)'
         : 'var(--t-text-secondary)';
  }

  ragBg(value: string): string {
    return value === 'red' ? 'rgba(239,68,68,0.12)'
         : value === 'amber' ? 'rgba(245,158,11,0.12)'
         : 'rgba(16,185,129,0.12)';
  }

  ragFg(value: string): string {
    return value === 'red' ? 'var(--t-red)'
         : value === 'amber' ? 'var(--t-amber)'
         : 'var(--t-green)';
  }

  healthBg(value: string): string {
    return value === 'on_track' ? 'rgba(16,185,129,0.12)'
         : value === 'at_risk' ? 'rgba(245,158,11,0.12)'
         : value === 'critical' ? 'rgba(239,68,68,0.12)'
         : 'var(--t-surface-raised)';
  }

  healthFg(value: string): string {
    return value === 'on_track' ? 'var(--t-green)'
         : value === 'at_risk' ? 'var(--t-amber)'
         : value === 'critical' ? 'var(--t-red)'
         : 'var(--t-text-secondary)';
  }
}
