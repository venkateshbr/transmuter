import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

interface MilestoneItem {
  id: string;
  initiative_id: string;
  name: string;
  description: string | null;
  owner_id: string | null;
  owner_name: string | null;
  priority: string;
  status: string;
  sort_order: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_end: string | null;
  pressure_score: string | null;
  pressure_level: string | null;
  checklist_total: number;
  checklist_done: number;
  dependency_count: number;
}

interface MilestoneDetail extends MilestoneItem {
  pressure_blast_radius: string | null;
  pressure_dep_urgency: string | null;
  pressure_cluster: string | null;
  pressure_slack: string | null;
  pressure_checklist: string | null;
  pressure_self_status: string | null;
  checklist: ChecklistItem[];
  dependencies: DependencyItem[];
}

interface ChecklistItem {
  id: string;
  milestone_id: string;
  text: string;
  completed: boolean;
  sort_order: number;
}

interface DependencyItem {
  id: string;
  upstream_milestone_id: string;
  upstream_name: string | null;
  downstream_milestone_id: string;
}

@Component({
  selector: 'app-milestones-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-4">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h3 class="text-base font-semibold" style="color:var(--t-text-primary)">
          Milestones<span style="color:var(--t-accent)">.</span>
          @if (!loading()) {
            <span class="text-sm font-normal ml-2"
                  style="color:var(--t-text-secondary)">
              {{ milestones().length }} total
            </span>
          }
        </h3>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="space-y-3">
          @for (i of [1,2,3,4]; track i) {
            <div class="card p-4 animate-pulse">
              <div class="flex items-center gap-4">
                <div class="w-3 h-3 rounded-full" style="background:var(--t-border)"></div>
                <div class="h-4 rounded w-48" style="background:var(--t-border)"></div>
                <div class="ml-auto h-4 rounded w-16" style="background:var(--t-border)"></div>
              </div>
            </div>
          }
        </div>
      }

      <!-- Milestone list -->
      @if (!loading() && milestones().length > 0) {
        <div class="space-y-2">
          @for (ms of milestones(); track ms.id) {
            <div class="card p-0 overflow-hidden">
              <!-- Row header -->
              <button class="w-full text-left px-4 py-3 flex items-center gap-3
                             hover:bg-[var(--t-surface-raised)] transition-colors"
                      (click)="toggleExpand(ms.id)"
                      [attr.aria-label]="'Toggle ' + ms.name + ' details'"
                      [attr.aria-expanded]="expandedId() === ms.id">
                <!-- Status dot -->
                <span class="w-2.5 h-2.5 rounded-full shrink-0"
                      [style.background]="statusColor(ms.status)"></span>

                <!-- Priority badge -->
                <span class="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded"
                      [class]="'badge-' + priorityBadge(ms.priority)">
                  {{ ms.priority }}
                </span>

                <!-- Pressure score -->
                @if (ms.pressure_score) {
                  <span class="text-xs font-mono font-semibold px-1.5 py-0.5 rounded"
                        [class]="'badge-' + (ms.pressure_level || 'gray')">
                    {{ ms.pressure_score }}
                  </span>
                }

                <!-- Name -->
                <span class="text-sm font-medium truncate"
                      style="color:var(--t-text-primary)">{{ ms.name }}</span>

                <!-- Owner -->
                @if (ms.owner_name) {
                  <span class="text-xs hidden md:inline"
                        style="color:var(--t-text-secondary)">{{ ms.owner_name }}</span>
                }

                <!-- Due date -->
                <span class="ml-auto text-xs font-mono shrink-0"
                      [style.color]="isOverdue(ms) ? 'var(--t-red)' : 'var(--t-text-secondary)'">
                  {{ ms.planned_end || '—' }}
                </span>

                <!-- Checklist progress -->
                @if (ms.checklist_total > 0) {
                  <span class="text-[10px] font-mono shrink-0"
                        style="color:var(--t-text-secondary)">
                    {{ ms.checklist_done }}/{{ ms.checklist_total }}
                  </span>
                }

                <!-- Expand chevron -->
                <svg class="w-4 h-4 transition-transform shrink-0"
                     [style.transform]="expandedId() === ms.id ? 'rotate(180deg)' : ''"
                     [style.color]="'var(--t-text-secondary)'"
                     fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </button>

              <!-- Expanded detail -->
              @if (expandedId() === ms.id && expandedDetail()) {
                <div class="border-t px-4 py-4 grid grid-cols-1 md:grid-cols-3 gap-4"
                     style="border-color:var(--t-border); background:var(--t-surface-raised)">
                  <!-- Left: description + checklist -->
                  <div class="md:col-span-2 space-y-4">
                    @if (expandedDetail()!.description) {
                      <p class="text-sm" style="color:var(--t-text-secondary)">
                        {{ expandedDetail()!.description }}
                      </p>
                    }

                    <!-- Checklist -->
                    @if (expandedDetail()!.checklist.length > 0) {
                      <div>
                        <p class="text-[10px] font-semibold uppercase mb-2"
                           style="color:var(--t-text-secondary)">Checklist</p>
                        @for (item of expandedDetail()!.checklist; track item.id) {
                          <label class="flex items-center gap-2 py-1 cursor-pointer group">
                            <input type="checkbox"
                                   [checked]="item.completed"
                                   (change)="onToggleChecklist(ms.id, item.id, !item.completed)"
                                   class="accent-[var(--t-accent)]"
                                   [attr.aria-label]="'Toggle ' + item.text"/>
                            <span class="text-sm transition-colors"
                                  [style.color]="item.completed ? 'var(--t-text-secondary)' : 'var(--t-text-primary)'"
                                  [style.textDecoration]="item.completed ? 'line-through' : 'none'">
                              {{ item.text }}
                            </span>
                          </label>
                        }
                      </div>
                    }

                    <!-- Dependencies -->
                    @if (expandedDetail()!.dependencies.length > 0) {
                      <div>
                        <p class="text-[10px] font-semibold uppercase mb-2"
                           style="color:var(--t-text-secondary)">Dependencies</p>
                        @for (dep of expandedDetail()!.dependencies; track dep.id) {
                          <div class="flex items-center gap-2 py-1">
                            <svg class="w-3.5 h-3.5" style="color:var(--t-accent)"
                                 fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round"
                                    stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                            </svg>
                            <span class="text-sm" style="color:var(--t-text-primary)">
                              {{ dep.upstream_name || dep.upstream_milestone_id }}
                            </span>
                          </div>
                        }
                      </div>
                    }
                  </div>

                  <!-- Right: Pressure panel -->
                  <div class="space-y-3">
                    <p class="text-[10px] font-semibold uppercase"
                       style="color:var(--t-text-secondary)">Pressure Breakdown</p>
                    @for (sub of pressureSubs(); track sub.label) {
                      <div>
                        <div class="flex justify-between text-xs mb-1">
                          <span style="color:var(--t-text-secondary)">{{ sub.label }}</span>
                          <span class="font-mono font-semibold"
                                style="color:var(--t-text-primary)">{{ sub.value }}/{{ sub.max }}</span>
                        </div>
                        <div class="h-1.5 rounded-full overflow-hidden"
                             style="background:var(--t-border)">
                          <div class="h-full rounded-full transition-all"
                               [style.width]="sub.pct + '%'"
                               [style.background]="sub.color"></div>
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && milestones().length === 0) {
        <div class="card text-center py-12">
          <p class="text-lg font-semibold" style="color:var(--t-text-primary)">
            No milestones yet<span style="color:var(--t-accent)">.</span>
          </p>
          <p class="text-sm mt-2" style="color:var(--t-text-secondary)">
            Milestones will appear here once added to this initiative.
          </p>
        </div>
      }
    </div>
  `,
})
export class MilestonesTabComponent implements OnInit {
  @Input() initiativeId = '';

  private readonly api = inject(ApiService);

  loading = signal(true);
  milestones = signal<MilestoneItem[]>([]);
  expandedId = signal<string | null>(null);
  expandedDetail = signal<MilestoneDetail | null>(null);

  pressureSubs = computed(() => {
    const d = this.expandedDetail();
    if (!d) return [];
    return [
      { label: 'Blast Radius', value: d.pressure_blast_radius || '0', max: '3.5', pct: this.pct(d.pressure_blast_radius, 3.5), color: 'var(--t-accent)' },
      { label: 'Dep. Urgency', value: d.pressure_dep_urgency || '0', max: '2.5', pct: this.pct(d.pressure_dep_urgency, 2.5), color: 'var(--t-accent)' },
      { label: 'Cluster', value: d.pressure_cluster || '0', max: '1.5', pct: this.pct(d.pressure_cluster, 1.5), color: 'var(--t-amber)' },
      { label: 'Slack', value: d.pressure_slack || '0', max: '1.5', pct: this.pct(d.pressure_slack, 1.5), color: 'var(--t-amber)' },
      { label: 'Checklist', value: d.pressure_checklist || '0', max: '0.5', pct: this.pct(d.pressure_checklist, 0.5), color: 'var(--t-green)' },
      { label: 'Self Status', value: d.pressure_self_status || '0', max: '0.5', pct: this.pct(d.pressure_self_status, 0.5), color: 'var(--t-green)' },
    ];
  });

  ngOnInit(): void {
    if (!this.initiativeId) { this.loading.set(false); return; }
    this.loadMilestones();
  }

  toggleExpand(id: string): void {
    if (this.expandedId() === id) {
      this.expandedId.set(null);
      this.expandedDetail.set(null);
      return;
    }
    this.expandedId.set(id);
    this.loadDetail(id);
  }

  isOverdue(ms: MilestoneItem): boolean {
    if (!ms.planned_end) return false;
    return ms.status !== 'complete' && ms.planned_end < new Date().toISOString().slice(0, 10);
  }

  statusColor(status: string): string {
    const map: Record<string, string> = {
      complete: 'var(--t-green)',
      in_progress: 'var(--t-accent)',
      overdue: 'var(--t-red)',
      not_started: 'var(--t-text-secondary)',
    };
    return map[status] || 'var(--t-text-secondary)';
  }

  priorityBadge(priority: string): string {
    const map: Record<string, string> = {
      high: 'red', medium: 'amber', low: 'green',
    };
    return map[priority] || 'gray';
  }

  onToggleChecklist(
    milestoneId: string, itemId: string, completed: boolean,
  ): void {
    this.api.put<ChecklistItem>(
      `/milestones/${milestoneId}/checklist/${itemId}`,
      { completed },
    ).subscribe({
      next: () => this.loadDetail(milestoneId),
      error: () => {},
    });
  }

  pct(val: string | null, max: number): number {
    if (!val) return 0;
    const n = parseFloat(val);
    if (isNaN(n) || max === 0) return 0;
    return Math.min((n / max) * 100, 100);
  }

  private loadMilestones(): void {
    const path = `/initiatives/${this.initiativeId}/milestones`;
    this.api.get<{ items: MilestoneItem[]; total: number }>(path).subscribe({
      next: (r: { items: MilestoneItem[] }) => {
        this.milestones.set(r.items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadDetail(id: string): void {
    this.api.get<MilestoneDetail>(`/milestones/${id}`).subscribe({
      next: (d: MilestoneDetail) => this.expandedDetail.set(d),
      error: () => this.expandedDetail.set(null),
    });
  }
}
