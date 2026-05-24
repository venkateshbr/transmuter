import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { CompactFilterToolbarComponent, type CompactFilterGroup } from '../../../shared/components/compact-filter-toolbar/compact-filter-toolbar.component';

interface InitiativeItem {
  id: string;
  initiative_code: string;
  name: string;
  business_unit_id: string | null;
  business_unit_name: string | null;
  workstream_id: string | null;
  workstream_name: string | null;
  owner_name: string | null;
  type: string | null;
  priority: string;
  rag_status: string;
  stage: string;
  country: string | null;
  tag: string | null;
  pressure_score: string | null;
  planned_value_base: string | null;
  planned_value_high: string | null;
  archived_at: string | null;
}

type PipelineMultiFilterKey = 'business_unit_id' | 'workstream_id' | 'priority' | 'tag';

interface FilterOption {
  id: string;
  name: string;
  business_unit_id?: string | null;
}

const STAGE_ORDER = ['scoping', 'in_progress', 'complete'] as const;
const STAGE_LABELS: Record<string, string> = {
  scoping: 'Scoping',
  in_progress: 'In-Progress',
  complete: 'Complete',
};
const FILTER_STATE_KEY = 'transmuter.filters.initiatives.pipeline';

@Component({
  selector: 'app-pipeline',
  standalone: true,
  imports: [RouterLink, FormsModule, CompactFilterToolbarComponent],
  styles: [`
    :host { display: block; }

    @keyframes shimmer {
      0%   { background-position: -800px 0; }
      100% { background-position:  800px 0; }
    }
    .skeleton {
      background: linear-gradient(
        90deg,
        var(--t-surface-raised) 25%,
        var(--t-border)         50%,
        var(--t-surface-raised) 75%
      );
      background-size: 800px 100%;
      animation: shimmer 1.4s infinite linear;
      border-radius: 4px;
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(5px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .row-enter { animation: fadeUp 0.25s ease both; }

    .rag-dot-red { box-shadow: 0 0 0 3px rgba(239,68,68,0.2); }

    .filter-panel {
      min-width: 150px;
      border: 1px solid var(--t-border);
      background: var(--t-surface-raised);
      padding: 8px;
    }
    .filter-label {
      margin-bottom: 6px;
      color: var(--t-text-tertiary);
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .filter-options {
      display: grid;
      gap: 4px;
      max-height: 76px;
      overflow-y: auto;
    }
    .filter-option {
      display: flex;
      align-items: center;
      gap: 6px;
      min-height: 24px;
      border: 1px solid var(--t-border);
      background: var(--t-surface);
      padding: 3px 6px;
      color: var(--t-text-secondary);
      font-size: 11px;
      font-weight: 700;
    }
    .filter-option input {
      accent-color: var(--t-accent);
    }
    .filter-option:has(input:checked) {
      border-color: var(--t-accent);
      background: var(--t-accent-soft);
      color: var(--t-text-primary);
    }

    .expand-area {
      display: grid;
      grid-template-rows: 0fr;
      transition: grid-template-rows 0.2s ease;
    }
    .expand-area.open { grid-template-rows: 1fr; }
    .expand-inner { overflow: hidden; }

    select {
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 8px center;
      padding-right: 26px !important;
    }
  `],
  template: `
<div class="min-h-screen" style="background:var(--t-bg)">

  <!-- PAGE HEADER -->
  <div class="px-8 pt-8 pb-5 border-b" style="border-color:var(--t-border)">
    <div class="flex items-start justify-between mb-5">
      <div>
        <h1 class="text-3xl font-bold tracking-tight" style="color:var(--t-text-primary)">
          Initiatives<span style="color:var(--t-accent)">.</span>
        </h1>
        <p class="text-sm mt-0.5" style="color:var(--t-text-secondary)">
          @if (loading()) { Loading portfolio&hellip; }
          @else {
            {{ total() }} initiative{{ total() === 1 ? '' : 's' }}
            across {{ activeStageCount() }} stage{{ activeStageCount() === 1 ? '' : 's' }}
          }
        </p>
      </div>

      <div class="flex items-center gap-3 pt-1">
        <!-- View toggle -->
        <div class="flex rounded-lg p-0.5 border text-xs"
             style="background:var(--t-surface-raised);border-color:var(--t-border)">
          <span class="px-3 py-1.5 rounded-md font-medium shadow-sm"
                style="background:var(--t-surface);color:var(--t-text-primary)">Pipeline</span>
          <a routerLink="/initiatives/matrix"
             class="px-3 py-1.5 rounded-md transition-colors duration-150"
             style="color:var(--t-text-secondary)">Matrix</a>
        </div>
        <a href="/api/initiatives/export"
           class="text-xs transition-colors duration-150"
           style="color:var(--t-text-secondary)">
          Export CSV ↗
        </a>
        @if (canManageInitiatives()) {
          <button class="btn-primary text-sm flex items-center gap-2"
                  (click)="openNewInitiative()"
                  aria-label="Create new initiative">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            New Initiative
          </button>
        }
      </div>
    </div>

    <app-compact-filter-toolbar
      [searchValue]="searchValue"
      searchPlaceholder="Search initiatives..."
      [groups]="filterGroups()"
      [hasFilters]="hasFilters()"
      clearTestId="initiatives-clear-filters"
      (searchValueChange)="onSearchChange($event)"
      (groupSelectionChange)="onFilterGroupChange($event)"
      (clearFilters)="clearFilters()" />
  </div>

  <!-- PIPELINE -->
  <div class="px-8 py-6">

    <!-- Loading skeletons -->
    @if (loading()) {
      <div class="space-y-1">
        @for (n of skeletons; track n) {
          <div class="flex items-center gap-4 px-4 rounded-lg border"
               style="padding-top:14px;padding-bottom:14px;background:var(--t-surface);border-color:var(--t-border)">
            <div class="skeleton rounded-full flex-shrink-0" style="width:8px;height:8px"></div>
            <div class="skeleton flex-shrink-0" style="height:12px;width:200px"></div>
            <div class="skeleton rounded-full flex-shrink-0" style="height:18px;width:48px"></div>
            <div class="skeleton rounded-md flex-shrink-0" style="height:18px;width:88px"></div>
            <div class="flex-1"></div>
            <div class="skeleton" style="height:12px;width:60px"></div>
            <div class="skeleton rounded-full" style="height:22px;width:28px"></div>
          </div>
        }
      </div>
    }

    <!-- Empty state -->
    @if (!loading() && total() === 0) {
      <div class="flex flex-col items-center justify-center py-28 text-center">
        <div class="rounded-2xl border flex items-center justify-center mb-5"
             style="width:64px;height:64px;background:var(--t-surface-raised);border-color:var(--t-border)">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
               stroke="var(--t-text-secondary)" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M9 21V9"/>
          </svg>
        </div>
        <h3 class="text-base font-semibold mb-1" style="color:var(--t-text-primary)">
          @if (hasFilters()) { No initiatives match these filters }
          @else { Portfolio is empty }
        </h3>
        <p class="text-sm mb-6 max-w-xs" style="color:var(--t-text-secondary)">
          @if (hasFilters()) { Try adjusting your filters to see more results. }
          @else if (canManageInitiatives()) { Start by creating your first transformation initiative. }
          @else { No initiatives are currently available for your role. }
        </p>
        @if (hasFilters()) {
          <button (click)="clearFilters()" class="btn-secondary text-sm">Clear filters</button>
        } @else if (canManageInitiatives()) {
          <button class="btn-primary text-sm flex items-center gap-2"
                  (click)="openNewInitiative()"
                  aria-label="Create new initiative">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            New Initiative
          </button>
        } @else {
          <a routerLink="/dashboard" class="btn-secondary text-sm">Back to dashboard</a>
        }
      </div>
    }

    <!-- Stage groups -->
    @if (!loading() && total() > 0) {
      <div class="space-y-4">
        @for (stage of stageOrder; track stage) {
          @let stageItems = grouped()[stage];
          @if (stageItems.length > 0) {
            <div class="rounded-xl overflow-hidden border" style="border-color:var(--t-border)">

              <!-- Stage header -->
              <div class="flex items-center justify-between px-4 py-2.5 border-b"
                   style="background:var(--t-surface-raised);border-color:var(--t-border)">
                <div class="flex items-center gap-3">
                  <div class="rounded-full flex-shrink-0"
                       style="width:3px;height:16px;background:var(--t-accent)"></div>
                  <span class="text-xs font-bold uppercase tracking-widest"
                        style="color:var(--t-text-primary);letter-spacing:.12em">
                    {{ stageLabels[stage] }}
                  </span>
                  <span class="text-xs rounded-full px-2 py-0.5 font-medium"
                        style="background:var(--t-border);color:var(--t-text-secondary)">
                    {{ stageItems.length }}
                  </span>
                </div>
                <span class="text-xs font-mono" style="color:var(--t-text-secondary)">
                  {{ stageTotalValue(stage) }}
                </span>
              </div>

              <!-- Column labels -->
              <div class="px-4 py-2 border-b"
                   style="background:var(--t-surface);border-color:var(--t-border);
                          display:grid;
                          grid-template-columns:12px 1fr 72px 112px 88px 28px 16px;
                          gap:16px;align-items:center">
                <span></span>
                <span class="text-[10px] font-semibold uppercase"
                      style="color:var(--t-text-secondary);letter-spacing:.1em">Initiative</span>
                <span class="text-[10px] font-semibold uppercase text-center"
                      style="color:var(--t-text-secondary)">Priority</span>
                <span class="text-[10px] font-semibold uppercase"
                      style="color:var(--t-text-secondary)">Workstream</span>
                <span class="text-[10px] font-semibold uppercase text-right"
                      style="color:var(--t-text-secondary)">Value</span>
                <span class="text-[10px] font-semibold uppercase text-center"
                      title="Pressure Score" style="color:var(--t-text-secondary)">P</span>
                <span></span>
              </div>

              <!-- Rows -->
              @for (item of stageItems; track item.id; let idx = $index) {
                <div class="border-b last:border-b-0" style="border-color:var(--t-border)">

                  <!-- Main row -->
                  <div class="row-enter px-4 items-center cursor-pointer"
                       [style.animation-delay]="(idx * 35) + 'ms'"
                       [style.background]="isExpanded(item.id) ? 'var(--t-surface-raised)' : 'var(--t-surface)'"
                       style="display:grid;
                              grid-template-columns:12px 1fr 72px 112px 88px 28px 16px;
                              gap:16px;padding-top:14px;padding-bottom:14px;
                              transition:background 0.15s ease"
                       (click)="toggleRow(item.id)"
                       (mouseover)="$event.currentTarget && setRowHover($event, true)"
                       (mouseout)="$event.currentTarget && setRowHover($event, false)">

                    <!-- RAG dot -->
                    <div class="rounded-full flex-shrink-0"
                         [class.rag-dot-red]="item.rag_status === 'red'"
                         [style.background]="ragColor(item.rag_status)"
                         style="width:8px;height:8px;justify-self:center"></div>

                    <!-- Code + Name -->
                    <div class="min-w-0 flex items-center gap-2">
                      <span class="text-[9px] font-mono flex-shrink-0 px-1.5 py-0.5 rounded bg-[var(--t-surface-raised)] border border-[var(--t-border)]"
                            style="color:var(--t-text-secondary)">
                        {{ item.initiative_code }}
                      </span>
                      <a [routerLink]="['/initiatives', item.id]"
                         (click)="$event.stopPropagation()"
                         class="text-sm font-bold truncate group-hover:text-[var(--t-accent)] transition-colors"
                         style="color:var(--t-text-primary)">
                        {{ item.name }}
                      </a>
                    </div>

                    <!-- Priority -->
                    <div class="flex justify-center">
                      <span class="text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg shadow-sm border"
                            [style.background]="priorityBg(item.priority)"
                            [style.color]="priorityFg(item.priority)"
                            [style.border-color]="priorityFg(item.priority) + '33'">
                        {{ item.priority }}
                      </span>
                    </div>

                    <!-- Workstream -->
                    <div>
                      @if (item.workstream_name) {
                        <span class="text-[10px] font-bold uppercase tracking-tighter px-2 py-1 rounded-xl block truncate border text-center shadow-sm"
                              style="color:var(--t-text-primary);background:var(--t-surface-raised);border-color:var(--t-border)">
                          {{ item.workstream_name }}
                        </span>
                      } @else {
                        <span class="text-xs block text-center opacity-30" style="color:var(--t-text-secondary)">—</span>
                      }
                    </div>

                    <!-- Value -->
                    <div class="text-right">
                      <span class="text-sm font-black text-[var(--t-text-primary)]">
                        {{ formatValue(item.planned_value_base) }}
                      </span>
                    </div>

                    <!-- Pressure -->
                    <div class="flex justify-center">
                      @if (item.pressure_score) {
                        <span class="text-xs font-black px-2 py-0.5 rounded bg-[var(--t-surface-raised)]"
                              [style.color]="pressureColor(item.pressure_score)">
                          {{ (+item.pressure_score).toFixed(1) }}
                        </span>
                      } @else {
                        <span class="text-xs opacity-30" style="color:var(--t-text-secondary)">—</span>
                      }
                    </div>

                    <!-- Chevron -->
                    <div class="flex justify-center">
                      <svg [style.transform]="isExpanded(item.id) ? 'rotate(90deg)' : ''"
                           style="transition:transform 0.2s ease"
                           width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M4.5 2.5L8 6l-3.5 3.5"
                              stroke="var(--t-text-secondary)" stroke-width="1.5"
                              stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                    </div>
                  </div>

                  <!-- Inline expand -->
                  <div class="expand-area" [class.open]="isExpanded(item.id)">
                    <div class="expand-inner">
                      <div class="px-12 py-4 grid gap-6 border-t text-xs"
                           style="grid-template-columns:repeat(5,1fr);background:var(--t-bg);border-color:var(--t-border)">
                        <div>
                          <p class="font-semibold uppercase mb-1.5"
                             style="font-size:9px;letter-spacing:.1em;color:var(--t-text-secondary)">RAG</p>
                          <div class="flex items-center gap-1.5">
                            <div class="rounded-full" style="width:6px;height:6px"
                                 [style.background]="ragColor(item.rag_status)"></div>
                            <span class="font-medium capitalize" style="color:var(--t-text-primary)">
                              {{ item.rag_status }}
                            </span>
                          </div>
                        </div>
                        <div>
                          <p class="font-semibold uppercase mb-1.5"
                             style="font-size:9px;letter-spacing:.1em;color:var(--t-text-secondary)">Type</p>
                          <span style="color:var(--t-text-primary)">{{ formatType(item.type) }}</span>
                        </div>
                        <div>
                          <p class="font-semibold uppercase mb-1.5"
                             style="font-size:9px;letter-spacing:.1em;color:var(--t-text-secondary)">Country</p>
                          <span style="color:var(--t-text-primary)">{{ item.country || '—' }}</span>
                        </div>
                        <div>
                          <p class="font-semibold uppercase mb-1.5"
                             style="font-size:9px;letter-spacing:.1em;color:var(--t-text-secondary)">Owner</p>
                          <span style="color:var(--t-text-primary)">{{ item.owner_name || '—' }}</span>
                        </div>
                        <div class="flex items-start pt-3">
                          <a [routerLink]="['/initiatives', item.id]"
                             (click)="$event.stopPropagation()"
                             class="text-xs font-semibold flex items-center gap-1"
                             style="color:var(--t-accent)">
                            View detail
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                              <path d="M2 5h6M5 2l3 3-3 3" stroke="currentColor"
                                    stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              }
            </div>
          }
        }
      </div>
    }
  </div>

</div>
  `,
})
export class PipelineComponent {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  readonly loading = signal(true);
  readonly total = signal(0);
  readonly initiatives = signal<InitiativeItem[]>([]);
  readonly expandedRows = signal(new Set<string>());
  readonly availableFilters = signal<{
    business_units: FilterOption[];
    workstreams: FilterOption[];
    priorities: FilterOption[];
    tags: FilterOption[];
  }>({
    business_units: [],
    workstreams: [],
    priorities: [],
    tags: [],
  });

  searchValue = '';
  ragFilter = '';
  businessUnitFilter: string[] = [];
  workstreamFilter: string[] = [];
  stageFilter = '';
  priorityFilter: string[] = [];
  tagFilter: string[] = [];

  readonly skeletons = Array.from({ length: 7 }, (_, i) => i);
  readonly stageOrder = STAGE_ORDER;
  readonly stageLabels = STAGE_LABELS;

  readonly grouped = computed(() => {
    const items = this.initiatives();
    return Object.fromEntries(
      STAGE_ORDER.map(s => [s, items.filter(i => i.stage === s)])
    ) as Record<string, InitiativeItem[]>;
  });

  readonly activeStageCount = computed(() =>
    STAGE_ORDER.filter(s => (this.grouped()[s]?.length ?? 0) > 0).length
  );

  private readonly router = inject(Router);

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.loadFilterOptions();
    this.route.queryParamMap.subscribe(params => {
      const hasQueryFilters = this.hasQueryFilters(params);
      if (hasQueryFilters) {
        this.searchValue = params.get('search') ?? '';
        this.ragFilter = params.get('rag_status') ?? '';
        this.businessUnitFilter = this.parseFilterParam(params.get('business_unit_id'));
        this.workstreamFilter = this.parseFilterParam(params.get('workstream_id'));
        this.stageFilter = params.get('stage') ?? '';
        this.priorityFilter = this.parseFilterParam(params.get('priority'));
        this.tagFilter = this.parseFilterParam(params.get('tag'));
      } else {
        this.restoreFilters();
      }
      this.reload(false);
    });
  }

  openNewInitiative(): void {
    if (!this.canManageInitiatives()) return;
    this.router.navigate(['/initiatives/new']);
  }

  canManageInitiatives(): boolean {
    return this.auth.getRole() === 'transformation_office';
  }

  reload(syncState = true): void {
    if (syncState) this.persistFilters();
    const params: Record<string, string | number> = { page_size: 200 };
    if (this.searchValue.trim()) params['search'] = this.searchValue.trim();
    if (this.ragFilter) params['rag_status'] = this.ragFilter;
    if (this.businessUnitFilter.length) params['business_unit_id'] = this.businessUnitFilter.join(',');
    if (this.workstreamFilter.length) params['workstream_id'] = this.workstreamFilter.join(',');
    if (this.stageFilter) params['stage'] = this.stageFilter;
    if (this.priorityFilter.length) params['priority'] = this.priorityFilter.join(',');
    if (this.tagFilter.length) params['tag'] = this.tagFilter.join(',');

    this.loading.set(true);
    this.api
      .get<{ items: InitiativeItem[]; total: number }>('/initiatives', params)
      .subscribe({
        next: r => { this.initiatives.set(r.items); this.total.set(r.total); this.loading.set(false); },
        error: () => this.loading.set(false),
      });
  }

  scheduleReload(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reload(), 300);
  }

  onSearchChange(value: string): void {
    this.searchValue = value;
    this.scheduleReload();
  }

  filterGroups(): CompactFilterGroup[] {
    return [
      {
        key: 'business_unit_id',
        label: 'Business Unit',
        options: this.availableFilters().business_units,
        selected: this.businessUnitFilter,
        testId: 'initiatives-filter-business-unit',
      },
      {
        key: 'workstream_id',
        label: 'Workstream',
        options: this.availableWorkstreams(),
        selected: this.workstreamFilter,
        testId: 'initiatives-filter-workstream',
      },
      {
        key: 'stage',
        label: 'Stage',
        mode: 'single',
        options: [
          { id: 'scoping', name: 'Scoping' },
          { id: 'in_progress', name: 'In-Progress' },
          { id: 'complete', name: 'Complete' },
        ],
        selected: this.stageFilter ? [this.stageFilter] : [],
      },
      {
        key: 'priority',
        label: 'Priority',
        options: this.availableFilters().priorities,
        selected: this.priorityFilter,
        testId: 'initiatives-filter-priority',
      },
      {
        key: 'tag',
        label: 'Tag',
        options: this.availableFilters().tags,
        selected: this.tagFilter,
        testId: 'initiatives-filter-tag',
      },
    ];
  }

  loadFilterOptions(): void {
    this.api.get<any>('/dashboard').subscribe({
      next: response => {
        const filters = response?.available_filters || {};
        this.availableFilters.set({
          business_units: filters.business_units || [],
          workstreams: filters.workstreams || [],
          priorities: filters.priorities || [
            { id: 'high', name: 'High' },
            { id: 'medium', name: 'Medium' },
            { id: 'low', name: 'Low' },
          ],
          tags: filters.tags || [],
        });
      },
      error: () => undefined,
    });
  }

  isFilterSelected(key: PipelineMultiFilterKey, value: string): boolean {
    return this.filterValues(key).includes(value);
  }

  onFilterGroupChange(change: { key: string; selected: string[] }): void {
    if (change.key === 'stage') {
      this.stageFilter = change.selected[0] || '';
      this.reload();
      return;
    }
    const key = change.key as PipelineMultiFilterKey;
    this.setFilterValues(key, change.selected);
    if (key === 'business_unit_id') {
      const visibleWorkstreamIds = new Set(this.availableWorkstreams().map(ws => ws.id));
      this.workstreamFilter = this.workstreamFilter.filter(wsId => visibleWorkstreamIds.has(wsId));
    }
    this.reload();
  }

  toggleFilter(key: PipelineMultiFilterKey, value: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const current = this.filterValues(key);
    this.onFilterGroupChange({
      key,
      selected: checked
        ? Array.from(new Set([...current, value]))
        : current.filter(item => item !== value),
    });
  }

  availableWorkstreams(): FilterOption[] {
    const workstreams = this.availableFilters().workstreams;
    if (!this.businessUnitFilter.length) return workstreams;
    const selectedBusinessUnits = new Set(this.businessUnitFilter);
    return workstreams.filter(ws => selectedBusinessUnits.has(ws.business_unit_id || ''));
  }

  hasFilters(): boolean {
    return !!(
      this.searchValue ||
      this.ragFilter ||
      this.businessUnitFilter.length ||
      this.workstreamFilter.length ||
      this.stageFilter ||
      this.priorityFilter.length ||
      this.tagFilter.length
    );
  }

  clearFilters(): void {
    this.searchValue = '';
    this.ragFilter = '';
    this.businessUnitFilter = [];
    this.workstreamFilter = [];
    this.stageFilter = '';
    this.priorityFilter = [];
    this.tagFilter = [];
    this.reload();
  }

  private persistFilters(): void {
    const state = this.currentFilterState();
    localStorage.setItem(FILTER_STATE_KEY, JSON.stringify(state));
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: this.queryParamsFromState(state),
      replaceUrl: true,
    });
  }

  private restoreFilters(): void {
    try {
      const raw = localStorage.getItem(FILTER_STATE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw) as Record<string, string | string[]>;
      this.searchValue = typeof state['search'] === 'string' ? state['search'] : '';
      this.ragFilter = typeof state['rag_status'] === 'string' ? state['rag_status'] : '';
      this.businessUnitFilter = Array.isArray(state['business_unit_id']) ? state['business_unit_id'] : [];
      this.workstreamFilter = Array.isArray(state['workstream_id']) ? state['workstream_id'] : [];
      this.stageFilter = typeof state['stage'] === 'string' ? state['stage'] : '';
      this.priorityFilter = Array.isArray(state['priority']) ? state['priority'] : [];
      this.tagFilter = Array.isArray(state['tag']) ? state['tag'] : [];
    } catch {
      localStorage.removeItem(FILTER_STATE_KEY);
    }
  }

  private currentFilterState(): Record<string, string | string[]> {
    return {
      search: this.searchValue.trim(),
      rag_status: this.ragFilter,
      business_unit_id: this.businessUnitFilter,
      workstream_id: this.workstreamFilter,
      stage: this.stageFilter,
      priority: this.priorityFilter,
      tag: this.tagFilter,
    };
  }

  private queryParamsFromState(state: Record<string, string | string[]>): Record<string, string | null> {
    return Object.fromEntries(
      Object.entries(state).map(([key, value]) => [
        key,
        Array.isArray(value) ? (value.length ? value.join(',') : null) : (value || null),
      ])
    );
  }

  private hasQueryFilters(params: { get: (key: string) => string | null }): boolean {
    return ['search', 'rag_status', 'business_unit_id', 'workstream_id', 'stage', 'priority', 'tag']
      .some(key => params.get(key));
  }

  private parseFilterParam(value: string | null): string[] {
    if (!value) return [];
    return value.split(',').map(item => item.trim()).filter(Boolean);
  }

  private filterValues(key: PipelineMultiFilterKey): string[] {
    if (key === 'business_unit_id') return this.businessUnitFilter;
    if (key === 'workstream_id') return this.workstreamFilter;
    if (key === 'priority') return this.priorityFilter;
    return this.tagFilter;
  }

  private setFilterValues(key: PipelineMultiFilterKey, values: string[]): void {
    if (key === 'business_unit_id') this.businessUnitFilter = values;
    if (key === 'workstream_id') this.workstreamFilter = values;
    if (key === 'priority') this.priorityFilter = values;
    if (key === 'tag') this.tagFilter = values;
  }

  toggleRow(id: string): void {
    const s = new Set(this.expandedRows());
    s.has(id) ? s.delete(id) : s.add(id);
    this.expandedRows.set(s);
  }

  isExpanded(id: string): boolean {
    return this.expandedRows().has(id);
  }

  setRowHover(event: MouseEvent, hovering: boolean): void {
    const el = event.currentTarget as HTMLElement;
    if (!this.isExpanded(el.getAttribute('data-id') ?? '')) {
      el.style.background = hovering ? 'var(--t-surface-raised)' : 'var(--t-surface)';
    }
  }

  ragColor(rag: string): string {
    return rag === 'red' ? 'var(--t-red)' : rag === 'amber' ? 'var(--t-amber)' : 'var(--t-green)';
  }

  priorityBg(p: string): string {
    return p === 'high' ? 'rgba(239,68,68,.12)' : p === 'medium' ? 'rgba(245,158,11,.12)' : 'rgba(107,114,128,.12)';
  }

  priorityFg(p: string): string {
    return p === 'high' ? '#f87171' : p === 'medium' ? '#fbbf24' : '#9ca3af';
  }

  pressureColor(score: string | null): string {
    if (!score) return 'var(--t-text-secondary)';
    const n = +score;
    return n >= 6.7 ? 'var(--t-red)' : n >= 3.4 ? 'var(--t-amber)' : 'var(--t-green)';
  }

  formatValue(v: string | null): string {
    if (!v) return '—';
    const n = parseFloat(v);
    if (!n) return '—';
    return n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}m`
         : n >= 1_000    ? `$${(n / 1_000).toFixed(0)}k`
                         : `$${n.toFixed(0)}`;
  }

  stageTotalValue(stage: string): string {
    const items = this.grouped()[stage] ?? [];
    const total = items.reduce((s, i) => s + (parseFloat(i.planned_value_base ?? '0') || 0), 0);
    return total > 0 ? this.formatValue(String(total)) : '';
  }

  capitalize(s: string): string {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  }

  formatType(t: string | null): string {
    if (!t) return '—';
    return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
