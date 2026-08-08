import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChild, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { RoadmapGanttComponent } from './roadmap-gantt.component';
import {
  PortfolioRoadmapResponse,
  RoadmapDependency,
  RoadmapLinkMode,
  RoadmapMilestone,
  RoadmapZoom,
} from './roadmap.models';

@Component({
  selector: 'app-roadmap',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RoadmapGanttComponent],
  template: `
    <main class="roadmap-page p-4 md:p-8 space-y-6 animate-fade-in">
      <header class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-[10px] font-black uppercase tracking-[0.22em] text-[var(--t-accent)]">Operations · Delivery control</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Roadmap Explorer<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-1 max-w-3xl text-sm text-[var(--t-text-secondary)]">See every milestone work window from start to finish, then trace what a delay puts at risk.</p>
        </div>
        <nav class="flex flex-wrap border border-[var(--t-border)] bg-[var(--t-surface)]" aria-label="Progress navigation">
          <a routerLink="/progress" class="roadmap-nav-link">Milestones</a>
          <span class="roadmap-nav-link roadmap-nav-active" aria-current="page">Roadmap</span>
          <a routerLink="/progress/action-items" class="roadmap-nav-link">Action items</a>
        </nav>
      </header>

      @if (loading()) {
        <section class="card p-12 text-center" aria-live="polite">
          <span class="material-icons animate-spin text-[var(--t-accent)]">progress_activity</span>
          <p class="mt-3 text-sm font-bold text-[var(--t-text-secondary)]">Loading the portfolio schedule…</p>
        </section>
      } @else if (error()) {
        <section class="border-l-4 border-[var(--t-red)] bg-[var(--t-surface)] p-6" role="alert">
          <h2 class="font-black text-[var(--t-text-primary)]">The roadmap could not be loaded</h2>
          <p class="mt-1 text-sm text-[var(--t-text-secondary)]">{{ error() }}</p>
          <button type="button" class="btn-secondary mt-4" (click)="loadRoadmap()">Try again</button>
        </section>
      } @else {
        <section class="roadmap-command-strip" aria-label="Roadmap summary">
          @for (metric of summaryMetrics(); track metric.label) {
            <div class="roadmap-metric">
              <p>{{ metric.label }}</p>
              <strong>{{ metric.value }}</strong>
              <span>{{ metric.note }}</span>
            </div>
          }
        </section>

        <section class="border border-[var(--t-border)] bg-[var(--t-surface)]">
          <div class="roadmap-controls">
            <label class="roadmap-control roadmap-search">
              <span>Find</span>
              <div class="relative">
                <span class="material-icons absolute left-3 top-2.5 text-sm text-[var(--t-text-tertiary)]">search</span>
                <input class="input-field w-full pl-9" [ngModel]="search()" (ngModelChange)="search.set($event)" placeholder="Milestone, initiative or owner" aria-label="Search roadmap">
              </div>
            </label>
            <label class="roadmap-control">
              <span>Workstream</span>
              <select class="input-field" [ngModel]="workstream()" (ngModelChange)="workstream.set($event)" aria-label="Filter by workstream">
                <option value="all">All workstreams</option>
                @for (item of workstreams(); track item) { <option [value]="item">{{ item }}</option> }
              </select>
            </label>
            <label class="roadmap-control">
              <span>Status</span>
              <select class="input-field" [ngModel]="status()" (ngModelChange)="status.set($event)" aria-label="Filter by milestone status">
                <option value="all">All statuses</option>
                @for (item of statuses(); track item) { <option [value]="item">{{ label(item) }}</option> }
              </select>
            </label>
            <label class="roadmap-control">
              <span>Scale</span>
              <select class="input-field" [ngModel]="zoom()" (ngModelChange)="zoom.set($event)" aria-label="Roadmap timeline scale">
                <option value="year">Year</option>
                <option value="quarter">Quarter</option>
                <option value="month">Month</option>
                <option value="week">Week</option>
              </select>
            </label>
            <label class="roadmap-control">
              <span>Dependency links</span>
              <select class="input-field" [ngModel]="linkMode()" (ngModelChange)="linkMode.set($event)" aria-label="Dependency link display mode">
                <option value="all">All links</option>
                <option value="blocking">Blocking and at risk</option>
                <option value="trace">Selected chain</option>
                <option value="hidden">Hidden</option>
              </select>
            </label>
            <div class="flex items-end gap-2">
              <button type="button" class="btn-secondary h-[42px]" (click)="gantt?.fitAll()" aria-label="Fit the full roadmap date range">Fit all</button>
              <button type="button" class="btn-ghost h-[42px]" (click)="gantt?.showToday()" aria-label="Scroll roadmap to today">Today</button>
            </div>
          </div>

          @if (filteredMilestones().length === 0) {
            <div class="p-12 text-center">
              <span class="material-icons text-3xl text-[var(--t-text-tertiary)]">event_busy</span>
              <h2 class="mt-3 text-base font-black text-[var(--t-text-primary)]">No milestones match these filters</h2>
              <p class="mt-1 text-sm text-[var(--t-text-secondary)]">Clear a filter to bring scheduled work back into view.</p>
              <button type="button" class="btn-secondary mt-4" (click)="resetFilters()">Clear filters</button>
            </div>
          } @else {
            <div class="hidden lg:block">
              <app-roadmap-gantt
                #gantt
                [milestones]="filteredMilestones()"
                [initiatives]="filteredInitiatives()"
                [dependencies]="dependencies()"
                [zoom]="zoom()"
                [linkMode]="linkMode()"
                [selectedMilestoneId]="selectedMilestoneId()"
                (milestoneSelected)="selectMilestone($event)" />
            </div>
            <div class="lg:hidden divide-y divide-[var(--t-border)]" data-testid="roadmap-mobile-list">
              <div class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3 text-xs font-bold text-[var(--t-text-secondary)]">Use a larger screen for the interactive Gantt. The complete chronological schedule remains available below.</div>
              @for (milestone of scheduledMilestones(); track milestone.id) {
                <button type="button" class="w-full p-4 text-left hover:bg-[var(--t-surface-raised)] focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[var(--t-accent)]" (click)="selectMilestone(milestone.id)" [attr.aria-label]="'Open ' + milestone.name">
                  <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">{{ milestone.initiative_code || 'Initiative' }} · {{ milestone.workstream_name || 'Unassigned' }}</span>
                  <span class="mt-1 block text-sm font-black text-[var(--t-text-primary)]">{{ milestone.name }}</span>
                  <span class="mt-2 block text-xs text-[var(--t-text-secondary)]">{{ milestone.planned_start || milestone.planned_end }} → {{ milestone.planned_end }}</span>
                </button>
              }
            </div>
          }
        </section>

        <div class="flex flex-wrap items-center gap-x-6 gap-y-2 px-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
          <span class="roadmap-legend"><i class="bg-[var(--t-green)]"></i> On track</span>
          <span class="roadmap-legend"><i class="bg-[var(--t-amber)]"></i> At risk</span>
          <span class="roadmap-legend"><i class="bg-[var(--t-red)]"></i> Due / blocking</span>
          <span class="roadmap-legend"><b></b> Dependency</span>
          <span class="ml-auto normal-case tracking-normal">Bars are planned work windows; diamonds are completion points.</span>
        </div>

        @if (unscheduledMilestones().length > 0) {
          <section class="border-l-4 border-[var(--t-amber)] bg-[var(--t-surface)] p-5" data-testid="roadmap-needs-scheduling">
            <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 class="text-base font-black text-[var(--t-text-primary)]">Needs scheduling</h2>
                <p class="mt-1 text-xs text-[var(--t-text-secondary)]">These milestones have no planned completion date and cannot be placed on the time axis.</p>
              </div>
              <span class="text-2xl font-black text-[var(--t-amber)]">{{ unscheduledMilestones().length }}</span>
            </div>
            <div class="mt-4 grid gap-px bg-[var(--t-border)] md:grid-cols-2 xl:grid-cols-3">
              @for (milestone of unscheduledMilestones(); track milestone.id) {
                <button type="button" class="bg-[var(--t-surface)] p-4 text-left hover:bg-[var(--t-surface-raised)]" (click)="selectMilestone(milestone.id)">
                  <span class="text-[10px] font-black uppercase text-[var(--t-accent)]">{{ milestone.initiative_code || 'Initiative' }}</span>
                  <span class="mt-1 block text-sm font-bold text-[var(--t-text-primary)]">{{ milestone.name }}</span>
                </button>
              }
            </div>
          </section>
        }
      }

      @if (selectedMilestone(); as selected) {
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm" (click)="closeMilestone()" data-testid="roadmap-milestone-modal">
          <article class="w-full max-w-4xl max-h-[90vh] overflow-y-auto border border-[var(--t-border-strong)] bg-[var(--t-surface)] shadow-2xl" (click)="$event.stopPropagation()" role="dialog" aria-modal="true" [attr.aria-label]="selected.name">
            <header class="border-b border-[var(--t-border)] bg-[var(--t-primary)] p-6 text-white">
              <div class="flex items-start justify-between gap-5">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-[0.2em] text-[var(--t-blue-light)]">{{ selected.initiative_code || 'Initiative' }} · {{ selected.initiative_name }}</p>
                  <h2 class="mt-2 text-2xl font-black">{{ selected.name }}</h2>
                  <p class="mt-2 text-xs text-white/70">{{ selected.planned_start || 'Start not set' }} → {{ selected.planned_end || 'Completion not set' }}</p>
                </div>
                <button type="button" class="h-9 w-9 border border-white/30 text-white hover:bg-white/10" aria-label="Close milestone detail" (click)="closeMilestone()"><span class="material-icons text-base">close</span></button>
              </div>
            </header>
            <div class="grid gap-6 p-6 lg:grid-cols-[1fr_280px]">
              <section>
                <div class="grid gap-px bg-[var(--t-border)] sm:grid-cols-3">
                  <div class="roadmap-detail-stat"><span>Status</span><strong>{{ label(selected.status) }}</strong></div>
                  <div class="roadmap-detail-stat"><span>Owner</span><strong>{{ selected.owner_name || 'Unassigned' }}</strong></div>
                  <div class="roadmap-detail-stat"><span>Pressure</span><strong>{{ selected.pressure_score || '0' }}</strong></div>
                </div>
                <div class="mt-6 grid gap-5 md:grid-cols-2">
                  <div class="roadmap-dependency-panel" data-testid="roadmap-upstream-dependencies">
                    <h3>Upstream dependencies <span>{{ upstreamDependencies().length }}</span></h3>
                    @for (dep of upstreamDependencies(); track dep.id) {
                      <button type="button" (click)="selectMilestone(dep.source)">{{ milestoneName(dep.source) }}<small>{{ dependencyLabel(dep) }}</small></button>
                    } @empty { <p>No upstream milestones linked.</p> }
                  </div>
                  <div class="roadmap-dependency-panel" data-testid="roadmap-downstream-dependencies">
                    <h3>Downstream dependents <span>{{ downstreamDependencies().length }}</span></h3>
                    @for (dep of downstreamDependencies(); track dep.id) {
                      <button type="button" (click)="selectMilestone(dep.target)">{{ milestoneName(dep.target) }}<small>{{ dependencyLabel(dep) }}</small></button>
                    } @empty { <p>No downstream milestones linked.</p> }
                  </div>
                </div>
              </section>
              <aside class="space-y-3">
                <button type="button" class="btn-primary w-full justify-center" (click)="traceSelected()"><span class="material-icons text-sm">account_tree</span> Trace dependency chain</button>
                <a
                  class="btn-secondary w-full justify-center"
                  [routerLink]="['/initiatives', selected.initiative_id]"
                  [queryParams]="{ tab: 'milestones', milestone: selected.id }">Open milestone details</a>
                <p class="border-t border-[var(--t-border)] pt-4 text-xs leading-5 text-[var(--t-text-secondary)]">Schedule changes remain controlled in the milestone workflow. This roadmap is read-only to prevent accidental portfolio rescheduling.</p>
              </aside>
            </div>
          </article>
        </div>
      }
    </main>
  `,
  styles: [`
    :host { display: block; }
    .roadmap-page { background: var(--t-bg); min-height: 100%; }
    .roadmap-nav-link { padding: .65rem 1rem; border-right: 1px solid var(--t-border); color: var(--t-text-secondary); font-size: .65rem; font-weight: 900; text-transform: uppercase; letter-spacing: .08em; }
    .roadmap-nav-link:last-child { border-right: 0; }
    .roadmap-nav-link:hover { background: var(--t-surface-raised); color: var(--t-text-primary); }
    .roadmap-nav-active { background: var(--t-primary); color: white; }
    .roadmap-command-strip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border: 1px solid var(--t-border); background: var(--t-primary); }
    .roadmap-metric { min-height: 90px; padding: 1rem 1.25rem; border-right: 1px solid rgba(255,255,255,.17); color: white; }
    .roadmap-metric:last-child { border-right: 0; }
    .roadmap-metric p { font-size: .58rem; font-weight: 900; text-transform: uppercase; letter-spacing: .14em; color: var(--t-blue-light); }
    .roadmap-metric strong { display: inline-block; margin-top: .35rem; font-size: 1.55rem; line-height: 1; }
    .roadmap-metric span { display: block; margin-top: .35rem; font-size: .65rem; color: rgba(255,255,255,.62); }
    .roadmap-controls { display: grid; grid-template-columns: minmax(220px, 1.5fr) repeat(4, minmax(140px, .75fr)) auto; gap: .75rem; padding: 1rem; border-bottom: 1px solid var(--t-border); background: var(--t-surface-raised); }
    .roadmap-control > span { display: block; margin-bottom: .35rem; font-size: .55rem; font-weight: 900; text-transform: uppercase; letter-spacing: .12em; color: var(--t-text-tertiary); }
    .roadmap-legend { display: inline-flex; align-items: center; gap: .4rem; }
    .roadmap-legend i { width: .55rem; height: .55rem; display: inline-block; }
    .roadmap-legend b { width: 1.5rem; display: inline-block; border-top: 2px solid var(--t-accent); }
    .roadmap-detail-stat { min-height: 84px; background: var(--t-surface-raised); padding: 1rem; }
    .roadmap-detail-stat span { display: block; font-size: .55rem; font-weight: 900; text-transform: uppercase; letter-spacing: .12em; color: var(--t-text-tertiary); }
    .roadmap-detail-stat strong { display: block; margin-top: .5rem; font-size: .8rem; color: var(--t-text-primary); }
    .roadmap-dependency-panel { border: 1px solid var(--t-border); }
    .roadmap-dependency-panel h3 { display: flex; justify-content: space-between; padding: .85rem 1rem; border-bottom: 1px solid var(--t-border); font-size: .7rem; font-weight: 900; text-transform: uppercase; letter-spacing: .06em; color: var(--t-text-primary); }
    .roadmap-dependency-panel h3 span { color: var(--t-accent); }
    .roadmap-dependency-panel button { display: block; width: 100%; padding: .8rem 1rem; border-bottom: 1px solid var(--t-border); text-align: left; font-size: .75rem; font-weight: 800; color: var(--t-text-primary); }
    .roadmap-dependency-panel button:hover { background: var(--t-surface-raised); }
    .roadmap-dependency-panel button small { display: block; margin-top: .25rem; color: var(--t-text-tertiary); font-size: .6rem; text-transform: uppercase; }
    .roadmap-dependency-panel p { padding: 1rem; font-size: .75rem; color: var(--t-text-secondary); }
    @media (max-width: 1200px) { .roadmap-controls { grid-template-columns: repeat(3, minmax(0, 1fr)); } .roadmap-search { grid-column: span 2; } }
    @media (max-width: 767px) { .roadmap-command-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .roadmap-metric { border-bottom: 1px solid rgba(255,255,255,.17); } .roadmap-metric:last-child { grid-column: span 2; } .roadmap-controls { grid-template-columns: 1fr; } .roadmap-search { grid-column: auto; } }
    @media (prefers-reduced-motion: reduce) { .animate-fade-in { animation: none; } }
  `],
})
export class RoadmapComponent implements OnInit {
  private readonly api = inject(ApiService);
  @ViewChild('gantt') gantt?: RoadmapGanttComponent;

  readonly roadmap = signal<PortfolioRoadmapResponse | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly search = signal('');
  readonly workstream = signal('all');
  readonly status = signal('all');
  readonly zoom = signal<RoadmapZoom>('quarter');
  readonly linkMode = signal<RoadmapLinkMode>('all');
  readonly selectedMilestoneId = signal<string | null>(null);

  readonly milestones = computed(() => this.roadmap()?.milestones || []);
  readonly dependencies = computed(() => this.roadmap()?.dependencies || []);
  readonly workstreams = computed(() => [...new Set(this.milestones().map(item => item.workstream_name).filter((item): item is string => !!item))].sort());
  readonly statuses = computed(() => [...new Set(this.milestones().map(item => item.status))].sort());
  readonly filteredMilestones = computed(() => {
    const query = this.search().trim().toLowerCase();
    return this.milestones().filter(item => {
      const matchesQuery = !query || [item.name, item.initiative_name, item.initiative_code, item.owner_name]
        .some(value => (value || '').toLowerCase().includes(query));
      const matchesWorkstream = this.workstream() === 'all' || item.workstream_name === this.workstream();
      const matchesStatus = this.status() === 'all' || item.status === this.status();
      return matchesQuery && matchesWorkstream && matchesStatus;
    });
  });
  readonly filteredInitiatives = computed(() => {
    const ids = new Set(this.filteredMilestones().map(item => item.initiative_id));
    return (this.roadmap()?.initiatives || []).filter(item => ids.has(item.id));
  });
  readonly scheduledMilestones = computed(() => this.filteredMilestones()
    .filter(item => !!(item.planned_start || item.planned_end))
    .sort((a, b) => (a.planned_start || a.planned_end || '').localeCompare(b.planned_start || b.planned_end || '')));
  readonly unscheduledMilestones = computed(() => this.filteredMilestones().filter(item => !item.planned_start && !item.planned_end));
  readonly selectedMilestone = computed(() => this.milestones().find(item => item.id === this.selectedMilestoneId()) || null);
  readonly upstreamDependencies = computed(() => this.dependencies().filter(item => item.target === this.selectedMilestoneId()));
  readonly downstreamDependencies = computed(() => this.dependencies().filter(item => item.source === this.selectedMilestoneId()));
  readonly summaryMetrics = computed(() => {
    const response = this.roadmap();
    const start = response?.range.earliest_start;
    const end = response?.range.latest_end;
    return [
      { label: 'Portfolio window', value: start && end ? `${start.slice(0, 7)} → ${end.slice(0, 7)}` : 'Dates needed', note: 'Earliest start to latest finish' },
      { label: 'Milestones', value: response?.stats.milestones || 0, note: `${response?.stats.initiatives || 0} initiatives` },
      { label: 'Dependencies', value: response?.stats.dependencies || 0, note: 'Cross-initiative included' },
      { label: 'Blocking links', value: response?.stats.blocking_links || 0, note: 'Needs intervention' },
      { label: 'Needs dates', value: response?.stats.missing_dates || 0, note: 'Incomplete schedule data' },
    ];
  });

  ngOnInit(): void { this.loadRoadmap(); }

  loadRoadmap(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.get<PortfolioRoadmapResponse>('/portfolio/roadmap').subscribe({
      next: response => { this.roadmap.set(response); this.loading.set(false); },
      error: error => {
        this.error.set(error?.error?.detail || 'Check your connection and try again.');
        this.loading.set(false);
      },
    });
  }

  selectMilestone(id: string): void { this.selectedMilestoneId.set(id); }
  closeMilestone(): void { this.selectedMilestoneId.set(null); }
  traceSelected(): void { this.linkMode.set('trace'); }
  resetFilters(): void { this.search.set(''); this.workstream.set('all'); this.status.set('all'); }
  milestoneName(id: string): string { return this.milestones().find(item => item.id === id)?.name || 'Milestone'; }
  label(value: string): string { return value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()); }
  dependencyLabel(dependency: RoadmapDependency): string {
    const lag = dependency.lag_days === 0 ? 'No lag' : `${dependency.lag_days > 0 ? '+' : ''}${dependency.lag_days} days`;
    return `${this.label(dependency.dependency_type)} · ${lag} · ${this.label(dependency.status)}`;
  }
}
