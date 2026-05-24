import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DashboardEchartCardComponent } from './dashboard-echart-card.component';
import { CompactFilterToolbarComponent, type CompactFilterGroup } from '../../shared/components/compact-filter-toolbar/compact-filter-toolbar.component';

type DashboardMultiFilterKey = 'business_unit_id' | 'workstream_id' | 'priority' | 'tag';
type ExecutiveBriefPersona = 'management' | 'investor' | 'owner';

interface FilterOption {
  id: string;
  name: string;
  business_unit_id?: string | null;
}

interface DecisionQueueItem {
  label: string;
  description: string;
  count: number;
  icon: string;
  route: string;
  queryParams?: Record<string, string>;
}

const DASHBOARD_FILTER_STATE_KEY = 'transmuter.filters.dashboard';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, DashboardEchartCardComponent, CompactFilterToolbarComponent],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Executive Hero Section -->
      <section class="executive-surface relative overflow-hidden p-8 shadow-2xl lg:p-10">
        <div class="absolute inset-y-0 right-0 w-1/3 border-l border-white/15 bg-white/5"></div>
        <div class="absolute right-10 top-8 h-24 w-24 border-t-4 border-r-4 border-[var(--t-blue-light)]/70"></div>
        <div class="absolute bottom-8 right-24 h-16 w-40 border-b-4 border-[var(--t-blue-light)]/45"></div>
        
        <div class="relative z-10 grid gap-8 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-4">
              <span class="h-2 w-8 bg-[var(--t-blue-light)]"></span>
              <span class="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">Portfolio Live Context</span>
            </div>
            <h1 class="text-4xl font-black tracking-tight leading-tight">
              Operational Excellence <br/>
              & Strategic Yield Dashboard<span class="text-[var(--t-blue-light)]">.</span>
            </h1>
            <p class="text-sm font-medium opacity-80 mt-4 max-w-xl leading-relaxed">
              Real-time synchronization across {{ data()?.summary?.total_initiatives }} strategic workstreams. 
              The current portfolio health score is <span class="font-black text-green-300">{{ getHealthScore() }}%</span> with 
              <span class="font-black text-amber-300">{{ data()?.summary?.pending_approvals }} pending gate decisions</span>.
            </p>
          </div>
          
          <div class="w-full max-w-xl xl:w-[30rem]">
              <div class="grid gap-3 sm:grid-cols-2">
                <button
                  (click)="openExecutiveBrief()"
                  data-testid="dashboard-executive-summary"
                  aria-label="Generate executive summary"
                  class="min-h-12 border border-white/20 bg-white/10 px-4 py-3 text-xs font-black uppercase tracking-widest transition-all hover:bg-white/20"
                >
                  {{ reporting() ? 'Preparing...' : 'Executive Brief' }}
                </button>
                <button
                  type="button"
                  class="executive-action-button min-h-12 bg-white px-4 py-3 text-xs font-black uppercase tracking-widest shadow-lg transition-all hover:shadow-[inset_0_-4px_0_var(--t-blue-light)]"
                  data-testid="dashboard-decision-queue"
                  aria-label="Open decision queue"
                  (click)="openDecisionQueue()">
                  Decision Queue
                </button>
              </div>
             <p class="mt-4 text-right text-[9px] font-bold uppercase tracking-widest opacity-60">Last System Sync: Just Now</p>
          </div>
        </div>
      </section>

      <!-- Portfolio Filters -->
      <section>
        <app-compact-filter-toolbar
          [showSearch]="false"
          [groups]="filterGroups()"
          [hasFilters]="hasDashboardFilters()"
          clearTestId="dashboard-clear-filters"
          (groupSelectionChange)="onFilterGroupChange($event)"
          (clearFilters)="clearFilters()" />
        @if (reportReady()) {
          <p class="mt-3 text-xs font-semibold text-[var(--t-accent)]" data-testid="dashboard-executive-summary-ready">
            Executive brief prepared from the current portfolio view.
          </p>
        }
      </section>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <a
          routerLink="/initiatives/pipeline"
          data-testid="dashboard-total-initiatives"
          class="card block p-6 border-l-4 border-[var(--t-accent)] cursor-pointer hover:-translate-y-0.5 hover:border-[var(--t-accent)] hover:shadow-xl transition-all"
          aria-label="Open all initiatives"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Initiatives</p>
          <p class="text-3xl font-bold text-[var(--t-text-primary)]">{{ data()?.summary?.total_initiatives || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            <span class="text-green-500">↑ 2</span> from last week
          </p>
        </a>
        <a
          routerLink="/initiatives/pipeline"
          [queryParams]="{ rag_status: 'red' }"
          data-testid="dashboard-at-risk"
          class="card block p-6 border-l-4 border-red-500 cursor-pointer hover:-translate-y-0.5 hover:border-red-500 hover:shadow-xl transition-all"
          aria-label="Open red at-risk initiatives"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">At Risk</p>
          <p class="text-3xl font-bold text-red-500">{{ data()?.summary?.at_risk || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            Requires immediate attention
          </p>
        </a>
        <a
          routerLink="/pmo/governance"
          [queryParams]="{ status: 'pending' }"
          data-testid="dashboard-pending-approvals"
          class="card block p-6 border-l-4 border-amber-500 cursor-pointer hover:-translate-y-0.5 hover:border-amber-500 hover:shadow-xl transition-all"
          aria-label="Open pending governance approvals"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Pending Approvals</p>
          <p class="text-3xl font-bold text-amber-500">{{ data()?.summary?.pending_approvals || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2">Gate submissions awaiting review</p>
        </a>
      </div>

      <!-- Value Matrix -->
      <section class="card overflow-hidden" data-testid="dashboard-value-matrix">
        <div class="executive-surface flex flex-col gap-4 border-b border-[var(--t-border)] p-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div class="mb-3 flex items-center gap-2">
              <span class="h-2 w-8 bg-[var(--t-blue-light)]"></span>
              <span class="text-[10px] font-black uppercase tracking-[0.2em] text-white/70">Gross Margin Uplift</span>
            </div>
            <h2 class="text-2xl font-black tracking-tight">Workstreams x Value Tags</h2>
            <p class="mt-2 max-w-2xl text-xs font-medium leading-relaxed text-white/70">
              Planned gross margin uplift ranges by operating workstream and initiative tag. Select a year and open any cell to inspect the initiatives behind the number.
            </p>
          </div>
          <label class="min-w-40 text-[10px] font-black uppercase tracking-widest text-white/70">
            Target Year
            <select
              class="executive-select mt-2 w-full border border-white/20 bg-white px-3 py-2 text-sm font-black"
              data-testid="dashboard-value-matrix-year"
              aria-label="Select value matrix target year"
              [value]="data()?.value_matrix?.selected_year || ''"
              (change)="onTargetYearChange($event)"
            >
              @for (year of data()?.value_matrix?.available_years || []; track year) {
                <option [value]="year">FY{{ year.toString().slice(-2) }}</option>
              }
            </select>
          </label>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[920px] border-collapse text-left">
            <thead>
              <tr class="executive-surface">
                <th class="w-56 border-r border-white/20 px-4 py-4 text-xs font-black uppercase tracking-widest">Workstream</th>
                @for (tag of data()?.value_matrix?.tags || []; track tag.id) {
                  <th class="border-r border-white/20 px-4 py-4 text-center text-xs font-black uppercase tracking-widest">{{ tag.label }}</th>
                }
                <th class="px-4 py-4 text-center text-xs font-black uppercase tracking-widest">
                  FY{{ ((data()?.value_matrix?.selected_year || '') + '').slice(-2) }} Total
                </th>
              </tr>
            </thead>
            <tbody>
              @for (row of data()?.value_matrix?.rows || []; track row.workstream_id || row.workstream_name) {
                <tr class="odd:bg-[var(--t-surface)] even:bg-[var(--t-surface-raised)]">
                  <th class="border-r border-[var(--t-border)] px-4 py-3 align-middle">
                    <span class="block text-sm font-black text-[var(--t-text-primary)]">{{ row.workstream_name }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.business_unit_name || 'Portfolio' }}</span>
                  </th>
                  @for (tag of data()?.value_matrix?.tags || []; track tag.id) {
                    <td class="border-r border-[var(--t-border)] px-2 py-2 text-center">
                      <button
                        type="button"
                        class="matrix-cell"
                        [class.matrix-cell-empty]="!row.cells?.[tag.id]?.initiative_count"
                        [attr.data-testid]="'dashboard-value-matrix-cell-' + (row.workstream_id || 'unassigned') + '-' + tag.id"
                        [attr.aria-label]="'Open initiatives for ' + row.workstream_name + ' ' + tag.label"
                        (click)="openMatrixCell(row.workstream_name, tag.label, row.cells?.[tag.id])"
                      >
                        <span class="block text-sm font-black">{{ formatRange(row.cells?.[tag.id]) }}</span>
                        <span class="text-[10px] font-bold text-[var(--t-text-tertiary)]">{{ row.cells?.[tag.id]?.initiative_count || 0 }} initiatives</span>
                      </button>
                    </td>
                  }
                  <td class="px-2 py-2 text-center">
                    <button
                      type="button"
                      class="matrix-cell matrix-cell-total"
                      [attr.data-testid]="'dashboard-value-matrix-row-total-' + (row.workstream_id || 'unassigned')"
                      [attr.aria-label]="'Open all value initiatives for ' + row.workstream_name"
                      (click)="openMatrixCell(row.workstream_name, 'FY total', row.total)"
                    >
                      <span class="block text-sm font-black">{{ formatRange(row.total) }}</span>
                      <span class="text-[10px] font-bold text-white/70">{{ row.total?.initiative_count || 0 }} initiatives</span>
                    </button>
                  </td>
                </tr>
              }
            </tbody>
            <tfoot>
              <tr class="executive-surface">
                <th class="border-r border-white/20 px-4 py-4 text-sm font-black uppercase tracking-widest">Total</th>
                @for (tag of data()?.value_matrix?.tags || []; track tag.id) {
                  <td class="border-r border-white/20 px-2 py-2 text-center">
                    <button
                      type="button"
                      class="matrix-cell matrix-cell-total"
                      [attr.aria-label]="'Open total initiatives for ' + tag.label"
                      (click)="openMatrixCell('All workstreams', tag.label, data()?.value_matrix?.totals?.cells?.[tag.id])"
                    >
                      <span class="block text-sm font-black">{{ formatRange(data()?.value_matrix?.totals?.cells?.[tag.id]) }}</span>
                      <span class="text-[10px] font-bold text-white/70">{{ data()?.value_matrix?.totals?.cells?.[tag.id]?.initiative_count || 0 }} initiatives</span>
                    </button>
                  </td>
                }
                <td class="px-2 py-2 text-center">
                  <button
                    type="button"
                    class="matrix-cell matrix-cell-total"
                    aria-label="Open all value matrix initiatives"
                    (click)="openMatrixCell('All workstreams', 'FY total', data()?.value_matrix?.totals?.total)"
                  >
                    <span class="block text-sm font-black">{{ formatRange(data()?.value_matrix?.totals?.total) }}</span>
                    <span class="text-[10px] font-bold text-white/70">{{ data()?.value_matrix?.totals?.total?.initiative_count || 0 }} initiatives</span>
                  </button>
                </td>
              </tr>
              <tr class="bg-[var(--t-surface)]">
                <th class="border-r border-[var(--t-border)] px-4 py-3 text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Value Bridge</th>
                <td class="px-4 py-3 text-center text-xs font-bold text-[var(--t-text-secondary)]" [attr.colspan]="(data()?.value_matrix?.tags?.length || 0) + 1">
                  Benefits {{ formatMoney(data()?.value_bridge?.benefits_base) }} - {{ formatMoney(data()?.value_bridge?.benefits_high) }}
                  <span class="mx-3 text-[var(--t-text-tertiary)]">|</span>
                  Costs {{ formatMoney(data()?.value_bridge?.costs_plan) }}
                  <span class="mx-3 text-[var(--t-text-tertiary)]">|</span>
                  Net {{ formatMoney(data()?.value_bridge?.net_base) }} - {{ formatMoney(data()?.value_bridge?.net_high) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <!-- Main Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Left Column: Pipeline & RAG -->
        <div class="lg:col-span-2 space-y-8">
          
          <!-- Pipeline by Stage -->
          <app-dashboard-echart-card kind="stage" [data]="data()" [stages]="stages" />

          <!-- RAG Breakdown -->
          <app-dashboard-echart-card kind="rag" [data]="data()" />
        </div>

        <!-- Right Column: Pressure & Milestones -->
        <div class="space-y-8">
          
          <!-- Pressure Gauge -->
          <app-dashboard-echart-card kind="pressure" [data]="data()" />

          <!-- My Milestones -->
          <div class="card p-6">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-lg font-bold text-[var(--t-text-primary)]">My Milestones</h3>
              <a routerLink="/progress" class="text-xs text-[var(--t-accent)] font-semibold">View all →</a>
            </div>
            <div class="space-y-4">
              @for (m of data()?.my_milestones; track m.id) {
                <a
                  [routerLink]="['/initiatives', m.initiative_id]"
                  [attr.data-testid]="'dashboard-milestone-' + m.id"
                  class="block p-3 rounded-lg border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] hover:border-[var(--t-accent)] transition-colors cursor-pointer"
                  [attr.aria-label]="'Open initiative for milestone ' + m.name"
                >
                  <p class="text-xs font-bold text-[var(--t-text-primary)] truncate">{{ m.name }}</p>
                  <p class="text-[10px] text-[var(--t-text-secondary)] mt-1 truncate">{{ m.initiative?.name }}</p>
                  <div class="flex justify-between items-center mt-3">
                    <span class="text-[10px] font-mono text-[var(--t-text-tertiary)]">{{ m.planned_end | date:'MMM d' }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full border"
                          [class.text-red-500]="m.status === 'delayed'"
                          [class.border-red-500]="m.status === 'delayed'">
                      {{ m.status | uppercase }}
                    </span>
                  </div>
                </a>
              }
              @if (!data()?.my_milestones?.length) {
                <p class="text-center py-8 text-xs text-[var(--t-text-tertiary)]">No upcoming milestones.</p>
              }
            </div>
          </div>

        </div>

      </div>

      <!-- Extended Widgets -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <section class="card p-6" data-testid="dashboard-my-actions">
          <div class="flex items-start justify-between gap-3 mb-5">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)]">My Actions</h3>
            <span class="material-icons text-[var(--t-text-tertiary)]" title="Assigned open meeting action items">help_outline</span>
          </div>
          <div class="space-y-3">
            @for (action of data()?.my_actions || []; track action.id) {
              <a routerLink="/progress/action-items" class="block rounded-lg border border-[var(--t-border)] p-3 hover:border-[var(--t-accent)] hover:bg-[var(--t-surface-raised)] transition-colors">
                <p class="text-sm font-bold text-[var(--t-text-primary)] truncate">{{ action.description }}</p>
                <p class="text-[11px] text-[var(--t-text-secondary)] mt-1 truncate">{{ action.initiatives?.name || 'Portfolio action' }}</p>
              </a>
            }
            @if (!(data()?.my_actions || []).length) {
              <p class="py-8 text-center text-xs text-[var(--t-text-tertiary)]">No assigned open actions.</p>
            }
          </div>
        </section>

        <section class="card p-6" data-testid="dashboard-kpi-pulse">
          <div class="flex items-start justify-between gap-3 mb-5">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)]">KPI Pulse</h3>
            <span class="material-icons text-[var(--t-text-tertiary)]" title="Latest actuals compared with base targets">help_outline</span>
          </div>
          <div class="flex items-end justify-between mb-4">
            <p class="text-4xl font-black text-[var(--t-accent)]">{{ data()?.kpi_pulse?.health_score || '0.0' }}%</p>
            <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ data()?.kpi_pulse?.hitting_base || 0 }} on target</p>
          </div>
          <div class="space-y-2">
            @for (kpi of data()?.kpi_pulse?.items || []; track kpi.id) {
              <a routerLink="/pmo/kpis" class="flex items-center justify-between gap-3 rounded-lg p-2 hover:bg-[var(--t-surface-raised)] transition-colors">
                <span class="text-xs font-semibold text-[var(--t-text-primary)] truncate">{{ kpi.name }}</span>
                <span class="text-[10px] font-bold uppercase" [class.text-green-500]="kpi.status === 'on_track'" [class.text-amber-500]="kpi.status !== 'on_track'">{{ kpi.status }}</span>
              </a>
            }
          </div>
        </section>

        <app-dashboard-echart-card kind="valueBridge" [data]="data()" />
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <app-dashboard-echart-card kind="riskHeatmap" [data]="data()" [heatmapLevels]="heatmapLevels" />

        <section class="card p-6" data-testid="dashboard-recent-activity">
          <div class="flex items-start justify-between gap-3 mb-5">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Recent Activity</h3>
            <span class="material-icons text-[var(--t-text-tertiary)]" title="Latest submitted status updates">help_outline</span>
          </div>
          <div class="space-y-3">
            @for (activity of data()?.recent_activity || []; track activity.id) {
              <a [routerLink]="['/initiatives', activity.initiative_id]" class="block rounded-lg border border-[var(--t-border)] p-3 hover:border-[var(--t-accent)] hover:bg-[var(--t-surface-raised)] transition-colors">
                <div class="flex items-center justify-between gap-3">
                  <p class="text-sm font-bold text-[var(--t-text-primary)] truncate">{{ activity.initiatives?.name || 'Initiative update' }}</p>
                  <span class="text-[10px] font-black uppercase" [style.color]="getRagColor(activity.rag_status)">{{ activity.rag_status }}</span>
                </div>
                <p class="text-xs text-[var(--t-text-secondary)] mt-1 line-clamp-2">{{ activity.summary || 'Status update submitted.' }}</p>
              </a>
            }
            @if (!(data()?.recent_activity || []).length) {
              <p class="py-8 text-center text-xs text-[var(--t-text-tertiary)]">No recent submitted updates.</p>
            }
          </div>
        </section>
      </div>

    </div>

    <!-- Onboarding / Welcome Modal -->
    @if (showWelcome()) {
      <div class="overlay flex items-center justify-center p-6 bg-black/40 backdrop-blur-md">
        <div class="card max-w-2xl w-full p-0 overflow-hidden shadow-2xl animate-scale-in">
           <div class="executive-surface h-48 p-10 relative overflow-hidden">
              <div class="absolute inset-y-0 right-0 w-1/3 border-l border-white/15 bg-white/5"></div>
              <div class="absolute right-8 top-8 h-20 w-20 border-t-4 border-r-4 border-[var(--t-blue-light)]/70"></div>
              <div class="relative z-10">
                 <h2 class="text-3xl font-black text-white leading-tight">Welcome to <br/>Transmuter Platform<span class="text-[var(--t-blue-light)]">.</span></h2>
                 <p class="text-white/70 text-xs font-bold uppercase tracking-widest mt-2">Executive Onboarding (May 2026 Release)</p>
              </div>
           </div>
           <div class="p-10 space-y-8 bg-[var(--t-surface)]">
              <div class="grid grid-cols-2 gap-6">
                 <div class="flex gap-4">
                    <div class="w-10 h-10 rounded-xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] shrink-0">
                       <span class="material-icons">dashboard</span>
                    </div>
                    <div>
                       <p class="text-sm font-black text-[var(--t-text-primary)]">Strategic Dashboard</p>
                       <p class="text-[10px] text-[var(--t-text-secondary)] mt-0.5">Real-time health & pressure scores.</p>
                    </div>
                 </div>
                 <div class="flex gap-4">
                    <div class="w-10 h-10 rounded-xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] shrink-0">
                       <span class="material-icons">psychology</span>
                    </div>
                    <div>
                       <p class="text-sm font-black text-[var(--t-text-primary)]">AI Assistant</p>
                       <p class="text-[10px] text-[var(--t-text-secondary)] mt-0.5">Natural language portfolio queries.</p>
                    </div>
                 </div>
              </div>
              <p class="text-sm text-[var(--t-text-secondary)] leading-relaxed">
                 You are logged in as the **Transformation Office Administrator**. You have full visibility across 4 workstreams and 24 strategic initiatives. 
              </p>
              <div class="flex gap-4 pt-4">
                 <button (click)="completeOnboarding()" class="flex-1 btn-primary py-4 font-black uppercase text-[10px] tracking-widest">Enter Command Center</button>
                 <button (click)="completeOnboarding()" class="px-8 py-4 border border-[var(--t-border)] font-black uppercase text-[10px] tracking-widest hover:bg-[var(--t-surface-raised)] transition-all">Quick Tour</button>
              </div>
           </div>
        </div>
      </div>
    }

    @if (selectedMatrixCell()) {
      <div class="overlay flex items-end justify-end bg-black/35 backdrop-blur-sm" (click)="closeMatrixCell()">
        <aside
          class="h-full w-full max-w-xl overflow-y-auto bg-[var(--t-surface)] shadow-2xl"
          data-testid="dashboard-value-matrix-drilldown"
          (click)="$event.stopPropagation()"
        >
          <div class="executive-surface sticky top-0 z-10 border-b border-[var(--t-border)] p-6">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60">{{ selectedMatrixCell()?.tagLabel }}</p>
                <h3 class="mt-2 text-2xl font-black">{{ selectedMatrixCell()?.rowLabel }}</h3>
                <p class="mt-2 text-sm font-bold text-[var(--t-blue-light)]">{{ formatRange(selectedMatrixCell()?.cell) }}</p>
              </div>
              <button type="button" class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10" aria-label="Close value matrix drilldown" (click)="closeMatrixCell()">Close</button>
            </div>
          </div>
          <div class="space-y-3 p-6">
            @for (initiative of selectedMatrixCell()?.cell?.initiatives || []; track initiative.id) {
              <a
                [routerLink]="['/initiatives', initiative.id]"
                class="block border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 transition-colors hover:border-[var(--t-accent)]"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ initiative.name }}</p>
                    <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ initiative.initiative_code }} | {{ initiative.stage }}</p>
                  </div>
                  <span class="text-[10px] font-black uppercase" [style.color]="getRagColor(initiative.rag_status)">{{ initiative.rag_status }}</span>
                </div>
                <div class="mt-4 grid grid-cols-3 gap-2 text-center">
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">GM Base</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.base) }}</p>
                  </div>
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">GM High</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.high) }}</p>
                  </div>
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">GM Actual</p>
                    <p class="text-xs font-black text-[var(--t-accent)]">{{ formatMoney(initiative.actual) }}</p>
                  </div>
                </div>
                <div class="mt-2 grid grid-cols-2 gap-2 text-center">
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Recurring Costs</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.recurring_costs_plan) }}</p>
                    <p class="mt-0.5 text-[9px] font-bold text-[var(--t-text-tertiary)]">Actual {{ formatMoney(initiative.recurring_costs_actual) }}</p>
                  </div>
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">One-Time Costs</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.one_time_costs_plan) }}</p>
                    <p class="mt-0.5 text-[9px] font-bold text-[var(--t-text-tertiary)]">Actual {{ formatMoney(initiative.one_time_costs_actual) }}</p>
                  </div>
                </div>
                <div class="mt-2 grid grid-cols-3 gap-2 text-center">
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Net Base</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.net_value_base) }}</p>
                  </div>
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Net High</p>
                    <p class="text-xs font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.net_value_high) }}</p>
                  </div>
                  <div class="bg-[var(--t-surface)] p-2">
                    <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Net Actual</p>
                    <p class="text-xs font-black text-[var(--t-accent)]">{{ formatMoney(initiative.net_value_actual) }}</p>
                  </div>
                </div>
              </a>
            }
            @if (!(selectedMatrixCell()?.cell?.initiatives || []).length) {
              <p class="py-16 text-center text-sm font-semibold text-[var(--t-text-tertiary)]">No initiatives contribute value in this cell yet.</p>
            }
          </div>
        </aside>
      </div>
    }

    @if (executiveBriefOpen()) {
      <div class="overlay flex items-end justify-end bg-black/35 backdrop-blur-sm" (click)="closeExecutiveBrief()">
        <aside
          class="h-full w-full max-w-3xl overflow-y-auto bg-[var(--t-surface)] shadow-2xl"
          data-testid="dashboard-executive-brief"
          (click)="$event.stopPropagation()"
        >
          <div class="executive-surface sticky top-0 z-10 border-b border-[var(--t-border)] p-6">
            <div class="flex items-start justify-between gap-5">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60">Management Report</p>
                <h3 class="mt-2 text-2xl font-black">Executive Brief</h3>
                <p class="mt-2 max-w-xl text-xs font-bold leading-5 text-white/70">
                  Live executive report signals for the current dashboard filters.
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  type="button"
                  class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                  data-testid="dashboard-executive-brief-pdf"
                  [disabled]="!executiveReport() || executiveReportLoading()"
                  aria-label="Export executive brief to PDF"
                  (click)="exportExecutiveBriefPdf()">
                  PDF
                </button>
                <button
                  type="button"
                  class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                  data-testid="dashboard-executive-brief-excel"
                  [disabled]="!executiveReport() || executiveReportLoading()"
                  aria-label="Export executive brief to Excel"
                  (click)="exportExecutiveBriefExcel()">
                  Excel
                </button>
                <a routerLink="/reports/control-tower" class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10" (click)="closeExecutiveBrief()">Full Report</a>
                <button type="button" class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10" aria-label="Close executive brief" (click)="closeExecutiveBrief()">Close</button>
              </div>
            </div>
          </div>

          <div class="space-y-6 p-6">
            <section class="flex flex-wrap items-end justify-between gap-4 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <div>
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Brief View</p>
                <div class="mt-3 inline-flex border border-[var(--t-border)] bg-[var(--t-surface)] p-1">
                  @for (persona of executivePersonas; track persona.id) {
                    <button
                      type="button"
                      class="px-3 py-2 text-[10px] font-black uppercase tracking-widest"
                      [class.bg-[var(--t-primary)]]="executivePersona() === persona.id"
                      [class.text-white]="executivePersona() === persona.id"
                      [class.text-[var(--t-text-secondary)]]="executivePersona() !== persona.id"
                      [attr.aria-pressed]="executivePersona() === persona.id"
                      (click)="setExecutivePersona(persona.id)">
                      {{ persona.label }}
                    </button>
                  }
                </div>
              </div>
              <div class="flex flex-wrap items-end gap-3">
                <label class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                  Target Year
                  <input
                    type="number"
                    class="input-field mt-2 h-10 w-28 text-sm"
                    [value]="filters().target_year || data()?.value_matrix?.selected_year || ''"
                    aria-label="Executive brief target year"
                    (change)="onExecutiveTargetYearChange($event)">
                </label>
                <a routerLink="/shared-costs" class="btn-secondary h-10 px-3 text-[10px]" (click)="closeExecutiveBrief()">Shared Costs</a>
              </div>
            </section>

            @if (executiveReportLoading()) {
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-8 text-sm font-bold text-[var(--t-text-secondary)]">Preparing executive brief...</div>
            } @else if (executiveReportError()) {
              <div class="border border-red-500/30 bg-red-500/10 p-5 text-sm font-bold text-red-500">{{ executiveReportError() }}</div>
            } @else {
              <section class="grid gap-3 md:grid-cols-5">
                @for (card of executiveBriefCards(); track card.label) {
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                    <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
                    <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ card.value }}</p>
                  </div>
                }
              </section>

              <section class="grid gap-4 lg:grid-cols-2">
                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                  <h4 class="text-sm font-black uppercase tracking-widest text-[var(--t-text-primary)]">Value Position</h4>
                  <div class="mt-4 grid gap-3">
                    @for (row of executiveValueRows(); track row.label) {
                      <div class="flex items-center justify-between border-b border-[var(--t-border)] pb-2 last:border-b-0">
                        <span class="text-xs font-bold text-[var(--t-text-secondary)]">{{ row.label }}</span>
                        <span class="text-sm font-black text-[var(--t-text-primary)]">{{ formatCurrency(row.value) }}</span>
                      </div>
                    }
                  </div>
                </div>

                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                  <h4 class="text-sm font-black uppercase tracking-widest text-[var(--t-text-primary)]">Dependency Risk</h4>
                  <div class="mt-4 grid grid-cols-2 gap-3">
                    @for (row of dependencyRiskRows(); track row.label) {
                      <div class="bg-[var(--t-surface-raised)] p-3">
                        <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.label }}</p>
                        <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ row.value }}</p>
                      </div>
                    }
                  </div>
                </div>
              </section>

              <section class="border border-[var(--t-border)] bg-[var(--t-surface)]">
                <div class="border-b border-[var(--t-border)] p-5">
                  <h4 class="text-sm font-black uppercase tracking-widest text-[var(--t-text-primary)]">Needs Attention</h4>
                </div>
                <div class="divide-y divide-[var(--t-border)]">
                  @for (item of executiveNeedsAttention(); track item.reason + item.initiative_id) {
                    <a routerLink="/reports/control-tower" class="block p-4 hover:bg-[var(--t-surface-raised)]" (click)="closeExecutiveBrief()">
                      <p class="text-sm font-black text-[var(--t-text-primary)]">{{ item.reason }}</p>
                      <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.initiative_id }}</p>
                    </a>
                  } @empty {
                    <p class="p-6 text-sm font-semibold text-[var(--t-text-secondary)]">No executive exceptions for the selected view.</p>
                  }
                </div>
              </section>

              <section class="border border-[var(--t-border)] bg-[var(--t-surface)]">
                <div class="flex items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
                  <h4 class="text-sm font-black uppercase tracking-widest text-[var(--t-text-primary)]">Initiative Burdening</h4>
                  <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Top exceptions</span>
                </div>
                <div class="overflow-x-auto">
                  <table class="w-full min-w-[720px] text-left text-xs">
                    <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      <tr>
                        <th class="px-4 py-3">Initiative</th>
                        <th class="px-4 py-3">RAG</th>
                        <th class="px-4 py-3">Realization</th>
                        <th class="px-4 py-3 text-right">Benefits</th>
                        <th class="px-4 py-3 text-right">Burdened Cost</th>
                        <th class="px-4 py-3 text-right">Net After Allocation</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (row of initiativeBurdeningRows(); track row.id) {
                        <tr class="border-t border-[var(--t-border)]">
                          <td class="px-4 py-3">
                            <a [routerLink]="['/initiatives', row.id]" class="font-black text-[var(--t-accent)]" (click)="closeExecutiveBrief()">
                              {{ row.initiative_code }} · {{ row.name }}
                            </a>
                          </td>
                          <td class="px-4 py-3 uppercase">{{ row.rag_status }}</td>
                          <td class="px-4 py-3 uppercase">{{ row.realization_status?.replace('_', ' ') }}</td>
                          <td class="px-4 py-3 text-right">{{ formatCurrency(row.benefits_plan) }}</td>
                          <td class="px-4 py-3 text-right">{{ formatCurrency(row.total_burdened_costs_plan) }}</td>
                          <td class="px-4 py-3 text-right font-black">{{ formatCurrency(row.net_after_allocation_plan) }}</td>
                        </tr>
                      } @empty {
                        <tr>
                          <td colspan="6" class="px-4 py-8 text-center text-sm font-semibold text-[var(--t-text-secondary)]">No burdening exceptions for the selected view.</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </section>
            }
          </div>
        </aside>
      </div>
    }

    @if (decisionQueueOpen()) {
      <div class="overlay flex items-end justify-end bg-black/35 backdrop-blur-sm" (click)="closeDecisionQueue()">
        <aside
          class="h-full w-full max-w-2xl overflow-y-auto bg-[var(--t-surface)] shadow-2xl"
          data-testid="dashboard-decision-queue-panel"
          (click)="$event.stopPropagation()"
        >
          <div class="executive-surface sticky top-0 z-10 border-b border-[var(--t-border)] p-6">
            <div class="flex items-start justify-between gap-5">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60">Actionable Exceptions</p>
                <h3 class="mt-2 text-2xl font-black">Decision Queue</h3>
                <p class="mt-2 max-w-xl text-xs font-bold leading-5 text-white/70">
                  A short queue of portfolio items that need an executive decision or follow-up.
                </p>
              </div>
              <button type="button" class="border border-white/20 px-3 py-2 text-xs font-black uppercase tracking-widest hover:bg-white/10" aria-label="Close decision queue" (click)="closeDecisionQueue()">Close</button>
            </div>
          </div>

          <div class="space-y-4 p-6">
            @if (executiveReportLoading()) {
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-8 text-sm font-bold text-[var(--t-text-secondary)]">Refreshing decision queue...</div>
            }
            @for (item of decisionQueueItems(); track item.label) {
              <a
                [routerLink]="item.route"
                [queryParams]="item.queryParams"
                class="grid gap-4 border border-[var(--t-border)] bg-[var(--t-surface)] p-5 transition-colors hover:border-[var(--t-accent)] hover:bg-[var(--t-surface-raised)] sm:grid-cols-[auto_minmax(0,1fr)_auto]"
                (click)="closeDecisionQueue()"
              >
                <div class="flex h-11 w-11 items-center justify-center bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                  <span class="material-icons text-lg">{{ item.icon }}</span>
                </div>
                <div>
                  <p class="text-sm font-black text-[var(--t-text-primary)]">{{ item.label }}</p>
                  <p class="mt-1 text-xs font-semibold leading-5 text-[var(--t-text-secondary)]">{{ item.description }}</p>
                </div>
                <div class="text-right">
                  <p class="text-2xl font-black text-[var(--t-text-primary)]">{{ item.count }}</p>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Open</p>
                </div>
              </a>
            }
          </div>
        </aside>
      </div>
    }
  `,
  styles: [`
    :host { display: block; }
    .executive-surface {
      background: var(--t-executive, #071f3c) !important;
      color: var(--t-executive-text, #ffffff) !important;
    }
    .executive-action-button,
    .executive-select {
      color: var(--t-executive, #071f3c) !important;
    }
    .filter-panel {
      min-height: 8.75rem;
      border: 1px solid var(--t-border);
      background: var(--t-surface-raised);
      padding: 0.75rem;
    }
    .filter-label {
      margin-bottom: 0.625rem;
      color: var(--t-text-tertiary);
      font-size: 0.625rem;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    .filter-options {
      display: grid;
      gap: 0.375rem;
      max-height: 6.5rem;
      overflow-y: auto;
    }
    .filter-option {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      min-height: 1.75rem;
      border: 1px solid var(--t-border);
      background: var(--t-surface);
      padding: 0.25rem 0.5rem;
      color: var(--t-text-secondary);
      font-size: 0.75rem;
      font-weight: 700;
    }
    .filter-option input {
      accent-color: var(--t-accent);
    }
    .filter-option:has(input:checked) {
      border-color: var(--t-accent);
      color: var(--t-text-primary);
      background: var(--t-accent-soft);
    }
    .matrix-cell {
      min-height: 4.25rem;
      width: 100%;
      border: 1px solid transparent;
      padding: 0.75rem 0.5rem;
      color: var(--t-text-primary);
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }
    .matrix-cell:hover {
      border-color: var(--t-accent);
      background: var(--t-accent-soft);
      transform: translateY(-1px);
    }
    .matrix-cell-empty {
      color: var(--t-text-tertiary);
      opacity: 0.62;
    }
    .matrix-cell-total {
      color: white;
      background: rgba(255,255,255,0.08);
    }
    .matrix-cell-total:hover {
      background: rgba(255,255,255,0.16);
      border-color: rgba(255,255,255,0.28);
    }
    .heatmap-cell {
      min-height: 8rem;
      border: 1px solid rgba(255,255,255,0.18);
      color: white;
      box-shadow: inset 0 0 22px rgba(7,31,60,0.1);
      transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }
    .heatmap-cell:hover {
      border-color: rgba(255,255,255,0.55);
      box-shadow: inset 0 0 0 2px rgba(255,255,255,0.18), 0 14px 30px rgba(7,31,60,0.16);
      transform: translateY(-1px);
    }
    .heatmap-count {
      color: white;
      font-size: 1.5rem;
      font-weight: 900;
      line-height: 1;
      text-shadow: 0 1px 4px rgba(7,31,60,0.28);
    }
    .heatmap-label {
      color: rgba(255,255,255,0.88);
      font-size: 0.56rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      margin-top: 0.75rem;
      text-transform: uppercase;
    }
    .heatmap-risk-critical {
      background: rgba(239,68,68,0.86);
    }
    .heatmap-risk-high {
      background: rgba(239,68,68,0.78);
    }
    .heatmap-risk-medium {
      background: rgba(245,158,11,0.82);
    }
    .heatmap-risk-low {
      background: rgba(34,197,94,0.78);
    }
    .animate-pulse-subtle {
      animation: pulse-subtle 3s infinite ease-in-out;
    }
    @keyframes pulse-subtle {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.8; }
    }
  `]
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  
  data = signal<any>(null);
  reporting = signal(false);
  reportReady = signal(false);
  showWelcome = signal(false);
  selectedMatrixCell = signal<any>(null);
  executiveBriefOpen = signal(false);
  decisionQueueOpen = signal(false);
  executiveReport = signal<any | null>(null);
  executiveReportLoading = signal(false);
  executiveReportError = signal<string | null>(null);
  executivePersona = signal<ExecutiveBriefPersona>('management');
  filters = signal({
    business_unit_id: [] as string[],
    workstream_id: [] as string[],
    priority: [] as string[],
    tag: [] as string[],
    target_year: '',
  });
  heatmapLevels = ['high', 'medium', 'low'];
  stages = [
    { id: 'scoping', label: 'Scoping' },
    { id: 'in_progress', label: 'In-Progress' },
    { id: 'complete', label: 'Complete' }
  ];
  readonly executivePersonas: { id: ExecutiveBriefPersona; label: string }[] = [
    { id: 'management', label: 'Management' },
    { id: 'investor', label: 'Investor' },
    { id: 'owner', label: 'Owner' },
  ];

  readonly filterGroups = computed<CompactFilterGroup[]>(() => [
    {
      key: 'business_unit_id',
      label: 'Business Unit',
      options: this.data()?.available_filters?.business_units || [],
      selected: this.filters().business_unit_id,
      testId: 'dashboard-filter-business-unit',
    },
    {
      key: 'workstream_id',
      label: 'Workstream',
      options: this.availableWorkstreams(),
      selected: this.filters().workstream_id,
      testId: 'dashboard-filter-workstream',
    },
    {
      key: 'priority',
      label: 'Priority',
      options: this.data()?.available_filters?.priorities || [],
      selected: this.filters().priority,
      testId: 'dashboard-filter-priority',
    },
    {
      key: 'tag',
      label: 'Tag',
      options: this.data()?.available_filters?.tags || [],
      selected: this.filters().tag,
      testId: 'dashboard-filter-tag',
    },
  ]);

  readonly executiveBriefCards = computed(() => {
    const summary = this.executiveReport()?.summary || {};
    return [
      { label: 'Initiatives', value: summary.initiative_count ?? this.data()?.summary?.total_initiatives ?? 0 },
      { label: 'Red', value: summary.red ?? this.data()?.rag_breakdown?.red ?? 0 },
      { label: 'Amber', value: summary.amber ?? this.data()?.rag_breakdown?.amber ?? 0 },
      { label: 'Realized', value: summary.realized ?? 0 },
      { label: 'Attention', value: summary.needs_attention ?? this.executiveNeedsAttention().length },
    ];
  });

  readonly executiveValueRows = computed(() => {
    const bridge = this.executiveReport()?.value_bridge || {};
    return [
      { label: 'Benefits Plan', value: bridge.benefits_plan },
      { label: 'Direct Costs', value: bridge.direct_costs_plan },
      { label: 'Allocated Costs', value: bridge.allocated_costs_plan },
      { label: 'Burdened Costs', value: bridge.total_burdened_costs_plan },
      { label: 'Net Before Allocation', value: bridge.net_before_allocation_plan },
      { label: 'Net After Allocation', value: bridge.net_after_allocation_plan },
    ];
  });

  readonly dependencyRiskRows = computed(() => {
    const risk = this.executiveReport()?.dependency_risk || {};
    return [
      { label: 'Total', value: risk.total || 0 },
      { label: 'Blocking', value: risk.blocking || 0 },
      { label: 'At Risk', value: risk.at_risk || 0 },
      { label: 'Overdue', value: risk.overdue || 0 },
      { label: 'Critical Path', value: risk.critical_path_risk || 0 },
      { label: 'Resolved', value: risk.resolved || 0 },
    ];
  });

  readonly initiativeBurdeningRows = computed(() => {
    const rows = this.executiveReport()?.initiatives || [];
    return rows
      .filter((row: any) =>
        ['red', 'amber'].includes(row.rag_status) ||
        Number(row.total_burdened_costs_plan || 0) > 0 ||
        Number(row.net_after_allocation_plan || 0) < 0
      )
      .slice(0, 8);
  });

  readonly decisionQueueItems = computed<DecisionQueueItem[]>(() => {
    const dashboard = this.data();
    const report = this.executiveReport();
    const risk = report?.dependency_risk || {};
    const attention = this.executiveNeedsAttention();
    const items: DecisionQueueItem[] = [
      {
        label: 'Pending Gate Decisions',
        description: 'Governance approvals waiting for transformation office review.',
        count: dashboard?.summary?.pending_approvals || 0,
        icon: 'gavel',
        route: '/pmo/governance',
        queryParams: { status: 'pending' } as Record<string, string>,
      },
      {
        label: 'Red Initiatives',
        description: 'Portfolio items marked red and requiring intervention.',
        count: dashboard?.summary?.at_risk || 0,
        icon: 'warning',
        route: '/initiatives/pipeline',
        queryParams: { rag_status: 'red' } as Record<string, string>,
      },
      {
        label: 'Blocking Dependencies',
        description: 'Active dependencies currently blocking portfolio delivery.',
        count: risk.blocking || 0,
        icon: 'account_tree',
        route: '/reports/control-tower',
      },
      {
        label: 'Overdue Dependencies',
        description: 'Dependency decisions or resolutions past their due date.',
        count: risk.overdue || 0,
        icon: 'event_busy',
        route: '/reports/control-tower',
      },
      {
        label: 'Executive Exceptions',
        description: 'Value, dependency, or realization signals needing attention.',
        count: attention.length,
        icon: 'radar',
        route: '/reports/control-tower',
      },
      {
        label: 'Assigned Actions',
        description: 'Open meeting actions assigned to you from the current portfolio view.',
        count: dashboard?.my_actions?.length || 0,
        icon: 'assignment',
        route: '/progress/action-items',
      },
    ].filter(item => item.count > 0);

    return items.length ? items : [{
      label: 'No Open Executive Decisions',
      description: 'The current portfolio view has no urgent decision queue items.',
      count: 0,
      icon: 'verified',
      route: '/dashboard',
    }];
  });

  ngOnInit() {
    this.route.queryParamMap.subscribe(params => {
      if (this.hasQueryFilters(params)) {
        this.filters.set({
          business_unit_id: this.parseFilterParam(params.get('business_unit_id')),
          workstream_id: this.parseFilterParam(params.get('workstream_id')),
          priority: this.parseFilterParam(params.get('priority')),
          tag: this.parseFilterParam(params.get('tag')),
          target_year: params.get('target_year') ?? '',
        });
      } else {
        this.restoreFilters();
      }
      this.loadDashboard(false);
    });
    this.checkOnboarding();
  }

  checkOnboarding() {
    this.auth.loadProfile().subscribe(user => {
      if (!user.onboarding_completed) {
        this.showWelcome.set(true);
      }
    });
  }

  completeOnboarding() {
    this.showWelcome.set(false);
    this.api.patch('/auth/me', { onboarding_completed: true }).subscribe(() => {
      this.auth.loadProfile().subscribe();
    });
  }

  loadDashboard(syncState = true) {
    if (syncState) this.persistFilters();
    const current = this.filters();
    const params: Record<string, string> = {};
    (['business_unit_id', 'workstream_id', 'priority', 'tag'] as DashboardMultiFilterKey[]).forEach(key => {
      if (current[key].length) params[key] = current[key].join(',');
    });
    if (current.target_year) params['target_year'] = current.target_year;
    this.api.get<any>('/dashboard', params).subscribe(d => this.data.set(d));
  }

  openExecutiveBrief(): void {
    this.executiveBriefOpen.set(true);
    this.reportReady.set(false);
    this.loadExecutiveReport(true);
  }

  closeExecutiveBrief(): void {
    this.executiveBriefOpen.set(false);
  }

  openDecisionQueue(): void {
    this.decisionQueueOpen.set(true);
    if (!this.executiveReport()) this.loadExecutiveReport(false);
  }

  closeDecisionQueue(): void {
    this.decisionQueueOpen.set(false);
  }

  private loadExecutiveReport(markReady: boolean): void {
    if (this.executiveReportLoading()) return;
    this.reporting.set(markReady);
    this.executiveReportLoading.set(true);
    this.executiveReportError.set(null);
    this.api.get<any>(this.executiveReportPath(), this.executiveReportParams()).subscribe({
      next: report => {
        this.executiveReport.set(report);
        this.executiveReportLoading.set(false);
        this.reporting.set(false);
        if (markReady) this.reportReady.set(true);
      },
      error: error => {
        this.executiveReportLoading.set(false);
        this.reporting.set(false);
        this.executiveReportError.set(error.error?.detail || 'Executive brief could not be prepared.');
      },
    });
  }

  setExecutivePersona(persona: ExecutiveBriefPersona): void {
    if (this.executivePersona() === persona) return;
    this.executivePersona.set(persona);
    this.executiveReport.set(null);
    this.loadExecutiveReport(this.executiveBriefOpen());
  }

  onExecutiveTargetYearChange(event: Event): void {
    const value = String((event.target as HTMLInputElement).value || '').trim();
    this.filters.update(current => ({ ...current, target_year: value }));
    this.persistFilters();
    this.executiveReport.set(null);
    this.loadExecutiveReport(this.executiveBriefOpen());
  }

  private executiveReportPath(): string {
    if (this.executivePersona() === 'owner') return '/reports/owner-cockpit';
    if (this.executivePersona() === 'investor') return '/reports/investor-summary';
    return '/reports/executive-control-tower';
  }

  private executiveReportParams(): Record<string, string> {
    const current = this.filters();
    const params: Record<string, string> = {};
    if (current.business_unit_id.length) params['business_unit_id'] = current.business_unit_id.join(',');
    if (current.workstream_id.length) params['workstream_id'] = current.workstream_id.join(',');
    if (current.tag.length) params['tag'] = current.tag.join(',');
    if (current.target_year) params['target_year'] = current.target_year;
    return params;
  }

  exportExecutiveBriefExcel(): void {
    const report = this.executiveReport();
    if (!report) return;

    const html = `
      <html>
        <head>
          <meta charset="utf-8">
          <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #9aaabe; padding: 8px; text-align: left; }
            th { background: #071f3c; color: #ffffff; }
            h1, h2 { color: #071f3c; }
          </style>
        </head>
        <body>
          <h1>Transmuter Executive Brief</h1>
          <p>Generated ${this.exportTimestamp()}</p>
          ${this.exportTable('Summary', this.executiveBriefCards().map(row => [row.label, row.value]))}
          ${this.exportTable('Value Position', this.executiveValueRows().map(row => [row.label, this.formatCurrency(row.value)]))}
          ${this.exportTable('Dependency Risk', this.dependencyRiskRows().map(row => [row.label, row.value]))}
          ${this.exportTable('Needs Attention', this.executiveNeedsAttention().map(row => [row.reason, row.initiative_id]))}
          ${this.exportTable('Initiative Burdening', this.initiativeBurdeningRows().map((row: any) => [
            `${row.initiative_code || ''} ${row.name || ''}`.trim(),
            row.rag_status || '',
            row.realization_status || '',
            this.formatCurrency(row.benefits_plan),
            this.formatCurrency(row.total_burdened_costs_plan),
            this.formatCurrency(row.net_after_allocation_plan),
          ]))}
        </body>
      </html>
    `;
    this.downloadBlob(
      html,
      `transmuter-executive-brief-${this.exportDateStamp()}.xls`,
      'application/vnd.ms-excel;charset=utf-8'
    );
  }

  exportExecutiveBriefPdf(): void {
    const report = this.executiveReport();
    if (!report) return;

    const popup = window.open('', '_blank');
    if (!popup) {
      this.downloadBlob(
        this.printableExecutiveBriefHtml(),
        `transmuter-executive-brief-${this.exportDateStamp()}.html`,
        'text/html;charset=utf-8'
      );
      return;
    }
    popup.document.open();
    popup.document.write(this.printableExecutiveBriefHtml());
    popup.document.close();
    popup.focus();
    popup.print();
  }

  private printableExecutiveBriefHtml(): string {
    return `
      <html>
        <head>
          <title>Transmuter Executive Brief</title>
          <style>
            @page { margin: 18mm; }
            body { color: #071f3c; font-family: Arial, sans-serif; font-size: 12px; }
            h1 { margin: 0 0 6px; font-size: 24px; }
            h2 { border-bottom: 2px solid #071f3c; font-size: 15px; margin-top: 24px; padding-bottom: 6px; }
            p { margin: 0 0 14px; color: #4c6178; }
            table { border-collapse: collapse; margin-top: 10px; width: 100%; }
            th, td { border: 1px solid #cfd8e2; padding: 8px; text-align: left; vertical-align: top; }
            th { background: #071f3c; color: white; font-size: 10px; text-transform: uppercase; }
            .summary { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin: 18px 0; }
            .metric { border: 1px solid #cfd8e2; padding: 10px; }
            .metric-label { color: #77879a; font-size: 9px; font-weight: 700; text-transform: uppercase; }
            .metric-value { color: #071f3c; font-size: 20px; font-weight: 900; margin-top: 8px; }
          </style>
        </head>
        <body>
          <h1>Transmuter Executive Brief</h1>
          <p>Generated ${this.exportTimestamp()}</p>
          <div class="summary">
            ${this.executiveBriefCards().map(row => `
              <div class="metric">
                <div class="metric-label">${this.escapeHtml(row.label)}</div>
                <div class="metric-value">${this.escapeHtml(String(row.value))}</div>
              </div>
            `).join('')}
          </div>
          ${this.exportTable('Value Position', this.executiveValueRows().map(row => [row.label, this.formatCurrency(row.value)]))}
          ${this.exportTable('Dependency Risk', this.dependencyRiskRows().map(row => [row.label, row.value]))}
          ${this.exportTable('Needs Attention', this.executiveNeedsAttention().map(row => [row.reason, row.initiative_id]))}
          ${this.exportTable('Initiative Burdening', this.initiativeBurdeningRows().map((row: any) => [
            `${row.initiative_code || ''} ${row.name || ''}`.trim(),
            row.rag_status || '',
            row.realization_status || '',
            this.formatCurrency(row.benefits_plan),
            this.formatCurrency(row.total_burdened_costs_plan),
            this.formatCurrency(row.net_after_allocation_plan),
          ]))}
        </body>
      </html>
    `;
  }

  private exportTable(title: string, rows: Array<Array<string | number>>): string {
    const safeRows = rows.length ? rows : [['None', '']];
    return `
      <h2>${this.escapeHtml(title)}</h2>
      <table>
        <tbody>
          ${safeRows.map(row => `
            <tr>
              ${row.map(cell => `<td>${this.escapeHtml(String(cell ?? ''))}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  private downloadBlob(content: string, filename: string, type: string): void {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  private exportTimestamp(): string {
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date());
  }

  private exportDateStamp(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  isFilterSelected(key: DashboardMultiFilterKey, value: string): boolean {
    return this.filters()[key].includes(value);
  }

  onFilterGroupChange(change: { key: string; selected: string[] }) {
    this.filters.update(current => {
      const key = change.key as DashboardMultiFilterKey;
      const next = { ...current, [key]: change.selected };
      if (key === 'business_unit_id') {
        const visibleWorkstreamIds = new Set(this.availableWorkstreams(change.selected).map(ws => ws.id));
        next.workstream_id = next.workstream_id.filter(wsId => visibleWorkstreamIds.has(wsId));
      }
      return next;
    });
    this.loadDashboard();
  }

  toggleFilter(key: DashboardMultiFilterKey, value: string, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    this.filters.update(current => {
      const nextValues = checked
        ? Array.from(new Set([...current[key], value]))
        : current[key].filter(item => item !== value);
      const next = { ...current, [key]: nextValues };
      if (key === 'business_unit_id') {
        const visibleWorkstreamIds = new Set(this.availableWorkstreams(next.business_unit_id).map(ws => ws.id));
        next.workstream_id = next.workstream_id.filter(wsId => visibleWorkstreamIds.has(wsId));
      }
      return next;
    });
    this.loadDashboard();
  }

  availableWorkstreams(selectedBusinessUnits = this.filters().business_unit_id): FilterOption[] {
    const workstreams = this.data()?.available_filters?.workstreams || [];
    if (!selectedBusinessUnits.length) return workstreams;
    const selected = new Set(selectedBusinessUnits);
    return workstreams.filter((ws: FilterOption) => selected.has(ws.business_unit_id || ''));
  }

  onTargetYearChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update(current => ({ ...current, target_year: value }));
    this.loadDashboard();
  }

  clearFilters() {
    this.filters.set({
      business_unit_id: [],
      workstream_id: [],
      priority: [],
      tag: [],
      target_year: '',
    });
    this.loadDashboard();
  }

  hasDashboardFilters(): boolean {
    const current = this.filters();
    return Boolean(
      current.business_unit_id.length ||
      current.workstream_id.length ||
      current.priority.length ||
      current.tag.length ||
      current.target_year
    );
  }

  private persistFilters(): void {
    const state = this.filters();
    localStorage.setItem(DASHBOARD_FILTER_STATE_KEY, JSON.stringify(state));
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        business_unit_id: state.business_unit_id.length ? state.business_unit_id.join(',') : null,
        workstream_id: state.workstream_id.length ? state.workstream_id.join(',') : null,
        priority: state.priority.length ? state.priority.join(',') : null,
        tag: state.tag.length ? state.tag.join(',') : null,
        target_year: state.target_year || null,
      },
      replaceUrl: true,
    });
  }

  private restoreFilters(): void {
    try {
      const raw = localStorage.getItem(DASHBOARD_FILTER_STATE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw) as Partial<ReturnType<typeof this.filters>>;
      this.filters.set({
        business_unit_id: Array.isArray(state.business_unit_id) ? state.business_unit_id : [],
        workstream_id: Array.isArray(state.workstream_id) ? state.workstream_id : [],
        priority: Array.isArray(state.priority) ? state.priority : [],
        tag: Array.isArray(state.tag) ? state.tag : [],
        target_year: typeof state.target_year === 'string' ? state.target_year : '',
      });
    } catch {
      localStorage.removeItem(DASHBOARD_FILTER_STATE_KEY);
    }
  }

  private parseFilterParam(value: string | null): string[] {
    if (!value) return [];
    return value.split(',').map(item => item.trim()).filter(Boolean);
  }

  private hasQueryFilters(params: { get: (key: string) => string | null }): boolean {
    return ['business_unit_id', 'workstream_id', 'priority', 'tag', 'target_year']
      .some(key => params.get(key));
  }

  getStagePercentage(stage: string): number {
    const total = this.data()?.summary?.total_initiatives || 1;
    const val = this.data()?.pipeline_by_stage?.[stage] || 0;
    return (val / total) * 100;
  }

  getRagPercentage(rag: string): number {
    const total = this.data()?.summary?.total_initiatives || 1;
    const val = this.data()?.rag_breakdown?.[rag] || 0;
    return (val / total) * 100;
  }

  getRagColor(rag: string): string {
    return rag === 'red' ? 'var(--t-red)' : rag === 'amber' ? 'var(--t-amber)' : 'var(--t-green)';
  }

  getHealthScore(): number {
    const total = this.data()?.summary?.total_initiatives || 0;
    if (total === 0) return 0;
    const red = this.data()?.rag_breakdown?.red || 0;
    return Math.round(((total - red) / total) * 100);
  }

  getPressureRotation(): string {
    const score = this.data()?.portfolio_pressure?.score || 0;
    // 0 to 10 score maps to -180 to 0 degrees rotation (approx)
    const deg = (score / 10) * 180 - 180;
    return `rotate(${deg}deg)`;
  }

  getPressureColor(): string {
    const score = this.data()?.portfolio_pressure?.score || 0;
    if (score < 3.4) return 'var(--t-green)';
    if (score < 6.7) return 'var(--t-amber)';
    return 'var(--t-red)';
  }

  getHeatmapCount(impact: string, likelihood: string): number {
    return this.data()?.risk_heatmap?.[`${impact}_${likelihood}`] || 0;
  }

  getHeatmapClass(impact: string, likelihood: string): string {
    const impactScore = impact === 'high' ? 3 : impact === 'medium' ? 2 : 1;
    const likelihoodScore = likelihood === 'high' ? 3 : likelihood === 'medium' ? 2 : 1;
    const score = impactScore * likelihoodScore;

    if (score >= 9) return 'heatmap-risk-critical';
    if (score >= 6) return 'heatmap-risk-high';
    if (score >= 4) return 'heatmap-risk-medium';
    return 'heatmap-risk-low';
  }

  formatMoney(value: string | null | undefined): string {
    const amount = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(amount);
  }

  formatCurrency(value: string | number | null | undefined): string {
    const amount = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(amount);
  }

  formatRange(cell: any): string {
    if (!cell) return '-';
    const base = Number(cell.base || 0);
    const high = Number(cell.high || 0);
    if (base === 0 && high === 0) return '-';
    return `${this.formatSignedMoney(cell.base)} - ${this.formatSignedMoney(cell.high)}`;
  }

  formatSignedMoney(value: string | null | undefined): string {
    const amount = Number(value || 0);
    const formatted = this.formatMoney(String(Math.abs(amount)));
    return amount < 0 ? `(${formatted})` : `+${formatted}`;
  }

  openMatrixCell(rowLabel: string, tagLabel: string, cell: any) {
    this.selectedMatrixCell.set({ rowLabel, tagLabel, cell });
  }

  closeMatrixCell() {
    this.selectedMatrixCell.set(null);
  }

  executiveNeedsAttention(): Array<{ reason: string; initiative_id: string }> {
    return this.executiveReport()?.needs_attention || [];
  }
}
