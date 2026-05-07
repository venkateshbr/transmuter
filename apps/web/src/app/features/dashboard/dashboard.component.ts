import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Executive Hero Section -->
      <section class="executive-surface relative overflow-hidden p-10 shadow-2xl">
        <div class="absolute inset-y-0 right-0 w-1/3 border-l border-white/15 bg-white/5"></div>
        <div class="absolute right-10 top-8 h-24 w-24 border-t-4 border-r-4 border-[var(--t-blue-light)]/70"></div>
        <div class="absolute bottom-8 right-24 h-16 w-40 border-b-4 border-[var(--t-blue-light)]/45"></div>
        
        <div class="relative z-10 flex flex-col md:flex-row justify-between items-center gap-8">
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
          
          <div class="flex-none flex flex-col items-end gap-4">
              <div class="flex gap-2">
                <button
                  (click)="generateReport()"
                  data-testid="dashboard-executive-summary"
                  aria-label="Generate executive summary"
                  class="border border-white/20 bg-white/10 px-6 py-3 text-xs font-black uppercase tracking-widest transition-all hover:bg-white/20"
                >
                  {{ reporting() ? 'Generating...' : 'Executive Summary' }}
                </button>
                <button routerLink="/initiatives/new" class="executive-action-button bg-white px-6 py-3 text-xs font-black uppercase tracking-widest shadow-lg transition-all hover:shadow-[inset_0_-4px_0_var(--t-blue-light)]">
                  + Executive Action
                </button>
              </div>
             <p class="text-[9px] font-bold opacity-60 uppercase tracking-widest mt-2">Last System Sync: Just Now</p>
          </div>
        </div>
      </section>

      <!-- Portfolio Filters -->
      <section class="card p-4">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
          <label class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
            Business Unit
            <select
              class="input-field mt-2"
              data-testid="dashboard-filter-business-unit"
              aria-label="Filter dashboard by business unit"
              [value]="filters().business_unit_id"
              (change)="onFilterChange('business_unit_id', $event)"
            >
              <option value="">All Business Units</option>
              @for (bu of data()?.available_filters?.business_units || []; track bu.id) {
                <option [value]="bu.id">{{ bu.name }}</option>
              }
            </select>
          </label>
          <label class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
            Workstream
            <select
              class="input-field mt-2"
              data-testid="dashboard-filter-workstream"
              aria-label="Filter dashboard by workstream"
              [value]="filters().workstream_id"
              (change)="onFilterChange('workstream_id', $event)"
            >
              <option value="">All Workstreams</option>
              @for (ws of data()?.available_filters?.workstreams || []; track ws.id) {
                <option [value]="ws.id">{{ ws.name }}</option>
              }
            </select>
          </label>
          <label class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
            RAG
            <select
              class="input-field mt-2"
              data-testid="dashboard-filter-rag"
              aria-label="Filter dashboard by RAG status"
              [value]="filters().rag_status"
              (change)="onFilterChange('rag_status', $event)"
            >
              <option value="">All RAG</option>
              @for (rag of data()?.available_filters?.rag_statuses || []; track rag.id) {
                <option [value]="rag.id">{{ rag.name }}</option>
              }
            </select>
          </label>
          <div class="flex items-end">
            <button
              type="button"
              class="btn-secondary w-full"
              data-testid="dashboard-clear-filters"
              aria-label="Clear dashboard filters"
              (click)="clearFilters()"
            >
              Clear Filters
            </button>
          </div>
        </div>
        @if (reportReady()) {
          <p class="mt-3 text-xs font-semibold text-[var(--t-accent)]" data-testid="dashboard-executive-summary-ready">
            Executive summary generated from the current portfolio view.
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
          <div class="card p-6">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Pipeline by Stage</h3>
            <div class="flex items-end gap-2 h-40">
              @for (stage of stages; track stage.id) {
                <a
                  routerLink="/initiatives/pipeline"
                  [queryParams]="{ stage: stage.id }"
                  [attr.data-testid]="'dashboard-stage-' + stage.id"
                  class="flex-1 flex flex-col items-center group cursor-pointer rounded-lg hover:bg-[var(--t-surface-raised)]/60 transition-colors"
                  [attr.aria-label]="'Open initiatives in ' + stage.label + ' stage'"
                >
                  <div class="w-full bg-[var(--t-accent-soft)] rounded-t-lg transition-all duration-500 group-hover:bg-[var(--t-accent)]"
                       [style.height.%]="getStagePercentage(stage.id)">
                    <div class="opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--t-surface)] text-[var(--t-text-primary)] text-[10px] font-bold px-2 py-1 rounded shadow-lg -mt-8 mx-auto w-fit">
                      {{ data()?.pipeline_by_stage?.[stage.id] || 0 }}
                    </div>
                  </div>
                  <div class="w-full h-1 bg-[var(--t-border)] mt-2"></div>
                  <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mt-3">
                    {{ stage.label }}
                  </p>
                </a>
              }
            </div>
          </div>

          <!-- RAG Breakdown -->
          <div class="card p-6">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Health Breakdown (RAG)</h3>
            <div class="flex items-center gap-8">
              <div class="flex-1 space-y-4">
                @for (rag of ['green', 'amber', 'red']; track rag) {
                  <a
                    routerLink="/initiatives/pipeline"
                    [queryParams]="{ rag_status: rag }"
                    [attr.data-testid]="'dashboard-rag-' + rag"
                    class="block space-y-1 rounded-lg p-2 -mx-2 cursor-pointer hover:bg-[var(--t-surface-raised)] transition-colors"
                    [attr.aria-label]="'Open ' + rag + ' initiatives'"
                  >
                    <div class="flex justify-between text-xs">
                      <span class="capitalize font-medium">{{ rag }}</span>
                      <span class="text-[var(--t-text-tertiary)]">{{ data()?.rag_breakdown?.[rag] || 0 }} initiatives</span>
                    </div>
                    <div class="h-2 bg-[var(--t-bg-page)] rounded-full overflow-hidden border border-[var(--t-border)]">
                      <div class="h-full transition-all duration-1000"
                           [style.width.%]="getRagPercentage(rag)"
                           [style.background]="getRagColor(rag)"></div>
                    </div>
                  </a>
                }
              </div>
              <div class="w-32 h-32 rounded-full border-8 border-[var(--t-surface-raised)] flex items-center justify-center relative">
                <div class="text-center">
                  <p class="text-2xl font-bold text-[var(--t-text-primary)]">
                    {{ getHealthScore() }}%
                  </p>
                  <p class="text-[10px] uppercase font-bold text-[var(--t-text-tertiary)]">Healthy</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Pressure & Milestones -->
        <div class="space-y-8">
          
          <!-- Pressure Gauge -->
          <a
            routerLink="/progress"
            data-testid="dashboard-pressure"
            class="card block p-6 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]/10 cursor-pointer hover:-translate-y-0.5 hover:border-[var(--t-accent)] hover:shadow-xl transition-all"
            aria-label="Open milestone tracker"
          >
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Portfolio Pressure</h3>
            <div class="relative pt-10 flex flex-col items-center">
               <div class="w-48 h-24 overflow-hidden relative">
                  <div class="w-48 h-48 rounded-full border-[16px] border-[var(--t-border)] absolute top-0 left-0"></div>
                  <div class="w-48 h-48 rounded-full border-[16px] border-[var(--t-accent)] absolute top-0 left-0 transition-all duration-1000"
                       style="clip-path: polygon(0 0, 100% 0, 100% 50%, 0 50%)"
                       [style.transform]="getPressureRotation()"></div>
               </div>
               <div class="text-center -mt-4">
                 <p class="text-3xl font-black text-[var(--t-text-primary)]">
                   {{ (data()?.portfolio_pressure?.score || 0).toFixed(1) }}
                 </p>
                 <p class="text-xs font-bold uppercase tracking-widest"
                    [style.color]="getPressureColor()">
                   {{ data()?.portfolio_pressure?.label }}
                 </p>
               </div>
            </div>
          </a>

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

        <section class="card p-6" data-testid="dashboard-value-bridge">
          <div class="flex items-start justify-between gap-3 mb-5">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Value Bridge</h3>
            <span class="material-icons text-[var(--t-text-tertiary)]" title="Portfolio benefits, costs, and net value">help_outline</span>
          </div>
          <div class="grid grid-cols-3 gap-3 text-center">
            <div class="rounded-lg bg-[var(--t-surface-raised)] p-3">
              <p class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">Base</p>
              <p class="text-sm font-black text-[var(--t-text-primary)]">{{ formatMoney(data()?.value_bridge?.net_base) }}</p>
            </div>
            <div class="rounded-lg bg-[var(--t-surface-raised)] p-3">
              <p class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">High</p>
              <p class="text-sm font-black text-[var(--t-text-primary)]">{{ formatMoney(data()?.value_bridge?.net_high) }}</p>
            </div>
            <div class="rounded-lg bg-[var(--t-surface-raised)] p-3">
              <p class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">Actual</p>
              <p class="text-sm font-black text-[var(--t-accent)]">{{ formatMoney(data()?.value_bridge?.net_actual) }}</p>
            </div>
          </div>
          <a routerLink="/initiatives/pipeline" class="mt-4 inline-flex text-xs font-bold text-[var(--t-accent)]">Open financial initiatives</a>
        </section>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section class="card p-6" data-testid="dashboard-risk-heatmap">
          <div class="flex items-start justify-between gap-3 mb-5">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Risk Heatmap</h3>
            <span class="material-icons text-[var(--t-text-tertiary)]" title="Open risks by impact and likelihood">help_outline</span>
          </div>
          <div class="grid grid-cols-3 gap-2">
            @for (impact of heatmapLevels; track impact) {
              @for (likelihood of heatmapLevels; track likelihood) {
                <a
                  routerLink="/pmo/risks"
                  [queryParams]="{ impact, likelihood }"
                  class="heatmap-cell aspect-square flex flex-col items-center justify-center"
                  [ngClass]="getHeatmapClass(impact, likelihood)"
                  [attr.aria-label]="'Open ' + impact + ' impact, ' + likelihood + ' likelihood risks'"
                  [attr.data-testid]="'dashboard-risk-' + impact + '-' + likelihood"
                >
                  <span class="heatmap-count">{{ getHeatmapCount(impact, likelihood) }}</span>
                  <span class="heatmap-label">{{ impact }}/{{ likelihood }}</span>
                </a>
              }
            }
          </div>
        </section>

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
  
  data = signal<any>(null);
  reporting = signal(false);
  reportReady = signal(false);
  showWelcome = signal(false);
  selectedMatrixCell = signal<any>(null);
  filters = signal({ business_unit_id: '', workstream_id: '', rag_status: '', target_year: '' });
  heatmapLevels = ['high', 'medium', 'low'];
  stages = [
    { id: 'scoping', label: 'Scoping' },
    { id: 'in_progress', label: 'In-Progress' },
    { id: 'complete', label: 'Complete' }
  ];

  ngOnInit() {
    this.loadDashboard();
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

  loadDashboard() {
    const params = Object.fromEntries(
      Object.entries(this.filters()).filter(([, value]) => !!value)
    );
    this.api.get<any>('/dashboard', params).subscribe(d => this.data.set(d));
  }

  onFilterChange(key: 'business_unit_id' | 'workstream_id' | 'rag_status', event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update(current => ({ ...current, [key]: value }));
    this.loadDashboard();
  }

  onTargetYearChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update(current => ({ ...current, target_year: value }));
    this.loadDashboard();
  }

  clearFilters() {
    this.filters.set({ business_unit_id: '', workstream_id: '', rag_status: '', target_year: '' });
    this.loadDashboard();
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

  generateReport() {
    if (this.reporting()) return;
    this.reporting.set(true);
    this.reportReady.set(false);
    
    setTimeout(() => {
      this.reporting.set(false);
      this.reportReady.set(true);
    }, 500);
  }
}
