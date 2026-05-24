import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

interface MilestoneItem {
  id: string;
  initiative_id: string;
  initiative_name?: string | null;
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

interface DependencyCandidateGroup {
  initiativeName: string;
  milestones: MilestoneItem[];
}

@Component({
  selector: 'app-milestones-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-4">
      <!-- Header -->
      <div class="flex items-center justify-between mb-2">
        <div>
          <h3 class="text-base font-bold" style="color:var(--t-text-primary)">
            Milestones<span style="color:var(--t-accent)">.</span>
          </h3>
          @if (!loading()) {
            <p class="text-[10px] font-semibold uppercase tracking-wider" style="color:var(--t-text-secondary)">
              {{ milestones().length }} milestones tracked
            </p>
          }
        </div>
        <button class="btn-primary text-xs flex items-center gap-2"
                (click)="onOpenAddModal()">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" 
               stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Milestone
        </button>
      </div>

      @if (!loading() && milestones().length > 0) {
        <div class="card p-3 flex flex-col lg:flex-row gap-3 lg:items-center">
          <div class="relative flex-1 min-w-0">
            <span class="material-icons absolute left-3 top-1/2 -translate-y-1/2 text-base" style="color:var(--t-text-secondary)">search</span>
            <input
              type="search"
              class="input-field pl-9 text-sm"
              placeholder="Search milestones..."
              [(ngModel)]="query"
              aria-label="Search milestones"/>
          </div>
          <div class="grid grid-cols-2 gap-3 lg:w-[360px]">
            <select class="input-field text-sm" [(ngModel)]="statusFilter" aria-label="Filter milestone status">
              <option value="all">All Status</option>
              <option value="not_started">Not Started</option>
              <option value="in_progress">In Progress</option>
              <option value="complete">Complete</option>
              <option value="overdue">Overdue</option>
            </select>
            <select class="input-field text-sm" [(ngModel)]="sortKey" aria-label="Sort milestones">
              <option value="manual">Manual Order</option>
              <option value="due">Due Date</option>
              <option value="pressure">Pressure</option>
              <option value="priority">Priority</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>
      }

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="space-y-3">
          @for (i of [1,2,3,4]; track i) {
            <div class="card p-4 animate-pulse">
              <div class="flex items-center gap-4">
                <div class="w-3 h-3 rounded-full" style="background:var(--t-border)"></div>
                <div class="h-4 rounded w-48" style="background:var(--t-border)"></div>
              </div>
            </div>
          }
        </div>
      }

      <!-- Milestone list -->
      @if (!loading() && milestones().length > 0) {
        <div class="space-y-2">
          @for (ms of filteredMilestones(); track ms.id) {
            <div class="card p-0 overflow-hidden group/row transition-all duration-300">
              <!-- Row header -->
              <div class="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--t-surface-raised)] transition-colors cursor-pointer"
                   (click)="toggleExpand(ms.id)">
                
                <!-- Status dot -->
                <div class="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                     [style.background]="statusColor(ms.status)"></div>

                <!-- Name & Meta -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold truncate" style="color:var(--t-text-primary)">{{ ms.name }}</span>
                    <span class="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0"
                          [class]="'badge-' + priorityBadge(ms.priority)">
                      {{ ms.priority }}
                    </span>
                  </div>
                  @if (ms.owner_name) {
                    <p class="text-[10px] font-medium" style="color:var(--t-text-secondary)">{{ ms.owner_name }}</p>
                  }
                </div>

                <!-- Pressure score (Bubble style) -->
                @if (ms.pressure_score) {
                  <div class="hidden sm:flex items-center justify-center w-8 h-8 rounded-full border-2 border-[var(--t-surface-raised)] transition-transform group-hover/row:scale-110"
                       [class]="'badge-' + (ms.pressure_level || 'gray')"
                       [title]="'Pressure: ' + ms.pressure_score">
                    <span class="text-[10px] font-bold">{{ ms.pressure_score }}</span>
                  </div>
                }

                <!-- Due date & Progress -->
                <div class="text-right shrink-0">
                  <p class="text-xs font-bold font-mono"
                     [style.color]="isOverdue(ms) ? 'var(--t-red)' : 'var(--t-text-primary)'">
                    {{ ms.planned_end || '—' }}
                  </p>
                  @if (ms.checklist_total > 0) {
                    <p class="text-[9px] font-bold uppercase tracking-tighter"
                       style="color:var(--t-text-secondary)">
                      {{ ms.checklist_done }}/{{ ms.checklist_total }} tasks
                    </p>
                  }
                </div>

                <div class="hidden md:flex items-center gap-1 shrink-0" (click)="$event.stopPropagation()">
                  <button class="btn-ghost p-1.5" title="Move earlier" aria-label="Move milestone earlier"
                          [disabled]="sortKey !== 'manual'"
                          (click)="moveMilestone(ms, -1)">
                    <span class="material-icons text-sm">arrow_upward</span>
                  </button>
                  <button class="btn-ghost p-1.5" title="Move later" aria-label="Move milestone later"
                          [disabled]="sortKey !== 'manual'"
                          (click)="moveMilestone(ms, 1)">
                    <span class="material-icons text-sm">arrow_downward</span>
                  </button>
                </div>

                <!-- Expand chevron -->
                <svg class="w-4 h-4 transition-transform shrink-0"
                     [style.transform]="expandedId() === ms.id ? 'rotate(180deg)' : ''"
                     [style.color]="'var(--t-text-secondary)'"
                     fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </div>

              <!-- Expanded detail -->
              @if (expandedId() === ms.id && expandedDetail()) {
                <div class="border-t px-5 py-5 grid grid-cols-1 lg:grid-cols-4 gap-8 animate-fade-in"
                     style="border-color:var(--t-border); background:var(--t-surface-raised)">
                  
                  <!-- Left: description + checklist + dependencies -->
                  <div class="lg:col-span-3 space-y-6">
                    @if (expandedDetail()!.description) {
                      <div>
                        <p class="text-[10px] font-bold uppercase tracking-wider mb-2" style="color:var(--t-text-secondary)">Description</p>
                        <p class="text-sm leading-relaxed" style="color:var(--t-text-primary)">
                          {{ expandedDetail()!.description }}
                        </p>
                      </div>
                    }

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div>
                        <p class="text-[10px] font-bold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">
                          Checklist ({{ expandedDetail()!.checklist_done }}/{{ expandedDetail()!.checklist_total }})
                        </p>
                        <div class="flex gap-2 mb-3">
                          <input class="input-field text-xs"
                                 placeholder="Add checklist item..."
                                 [(ngModel)]="checklistDraft"
                                 aria-label="New checklist item"/>
                          <button class="btn-secondary px-3" title="Add checklist item" aria-label="Add checklist item"
                                  [disabled]="!checklistDraft.trim()"
                                  (click)="addChecklistItem(ms.id)">
                            <span class="material-icons text-sm">add_task</span>
                          </button>
                        </div>
                        @if (expandedDetail()!.checklist.length > 0) {
                          <div class="space-y-1.5">
                            @for (item of expandedDetail()!.checklist; track item.id) {
                              <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--t-surface)] transition-all cursor-pointer group/item">
                                <input type="checkbox"
                                       [checked]="item.completed"
                                       (change)="onToggleChecklist(ms.id, item.id, !item.completed)"
                                       class="w-4 h-4 rounded border-[var(--t-border)] text-[var(--t-accent)] focus:ring-[var(--t-accent-ring)]"/>
                                <span class="text-sm transition-all flex-1"
                                      [style.color]="item.completed ? 'var(--t-text-secondary)' : 'var(--t-text-primary)'"
                                      [style.textDecoration]="item.completed ? 'line-through' : 'none'">
                                  {{ item.text }}
                                </span>
                                <button type="button"
                                        class="btn-ghost p-1 opacity-0 group-hover/item:opacity-100"
                                        title="Delete checklist item"
                                        aria-label="Delete checklist item"
                                        (click)="$event.preventDefault(); deleteChecklistItem(ms.id, item.id)">
                                  <span class="material-icons text-sm">delete</span>
                                </button>
                              </label>
                            }
                          </div>
                        } @else {
                          <p class="text-xs font-medium rounded-lg border border-dashed p-3" style="border-color:var(--t-border); color:var(--t-text-secondary)">
                            No checklist items yet.
                          </p>
                        }
                      </div>

                      <div>
                        <p class="text-[10px] font-bold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">Blocking Dependencies</p>
                        <div class="flex gap-2 mb-3">
                          <select class="input-field text-xs"
                                  [(ngModel)]="dependencyDraft"
                                  aria-label="Select upstream dependency">
                            <option value="">Select upstream milestone</option>
                            @for (group of dependencyCandidateGroups(ms.id); track group.initiativeName) {
                              <optgroup [label]="group.initiativeName">
                                @for (candidate of group.milestones; track candidate.id) {
                                  <option [value]="candidate.id">{{ dependencyCandidateLabel(candidate) }}</option>
                                }
                              </optgroup>
                            }
                          </select>
                          <button class="btn-secondary px-3"
                                  title="Add dependency"
                                  aria-label="Add dependency"
                                  [disabled]="!dependencyDraft"
                                  (click)="addDependency(ms.id)">
                            <span class="material-icons text-sm">link</span>
                          </button>
                        </div>
                        @if (expandedDetail()!.dependencies.length > 0) {
                          <div class="space-y-2">
                            @for (dep of expandedDetail()!.dependencies; track dep.id) {
                              <div class="flex items-center gap-3 p-2 rounded-lg bg-[var(--t-surface)] border border-[var(--t-border)] group/dep">
                                <span class="material-icons text-sm" style="color:var(--t-red)">link_off</span>
                                <span class="text-xs font-medium flex-1" style="color:var(--t-text-primary)">
                                  {{ dep.upstream_name || 'Upstream Milestone' }}
                                </span>
                                <button class="btn-ghost p-1 opacity-0 group-hover/dep:opacity-100"
                                        title="Remove dependency"
                                        aria-label="Remove dependency"
                                        (click)="deleteDependency(ms.id, dep.id)">
                                  <span class="material-icons text-sm">close</span>
                                </button>
                              </div>
                            }
                          </div>
                        } @else {
                          <p class="text-xs font-medium rounded-lg border border-dashed p-3" style="border-color:var(--t-border); color:var(--t-text-secondary)">
                            No upstream blockers linked.
                          </p>
                        }
                      </div>
                    </div>
                  </div>

                  <!-- Right: Pressure panel -->
                  <div class="card p-4 space-y-4" style="background:var(--t-surface)">
                    <div class="grid grid-cols-1 gap-2">
                      <select class="input-field text-xs"
                              [ngModel]="ms.status"
                              aria-label="Milestone status"
                              (ngModelChange)="updateMilestone(ms.id, { status: $event })">
                        <option value="not_started">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="complete">Complete</option>
                        <option value="overdue">Overdue</option>
                      </select>
                      @if (confirmDeleteId() === ms.id) {
                        <div class="flex gap-2 justify-center">
                          <button class="btn-ghost text-[9px] font-black uppercase text-red-600 bg-red-50 py-1" (click)="deleteMilestone(ms.id)">Confirm</button>
                          <button class="btn-ghost text-[9px] font-black uppercase" (click)="confirmDeleteId.set(null)">Cancel</button>
                        </div>
                      } @else {
                        <button class="btn-ghost text-xs justify-center"
                                aria-label="Delete milestone"
                                (click)="confirmDeleteId.set(ms.id)">
                          <span class="material-icons text-sm">delete</span>
                          Delete Milestone
                        </button>
                      }
                    </div>
                    <div>
                      <p class="text-[10px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Total Pressure</p>
                      <div class="flex items-baseline gap-1">
                        <span class="text-2xl font-bold" style="color:var(--t-text-primary)">{{ ms.pressure_score || '0' }}</span>
                        <span class="text-xs font-semibold uppercase" [class]="'text-' + (ms.pressure_level || 'gray') + '-500'">{{ ms.pressure_level || 'Normal' }}</span>
                      </div>
                    </div>
                    
                    <div class="space-y-3 pt-2 border-t" style="border-color:var(--t-border)">
                      @for (sub of pressureSubs(); track sub.label) {
                        <div>
                          <div class="flex justify-between text-[10px] font-bold uppercase mb-1">
                            <span style="color:var(--t-text-secondary)">{{ sub.label }}</span>
                            <span style="color:var(--t-text-primary)">{{ sub.value }}/{{ sub.max }}</span>
                          </div>
                          <div class="h-1.5 rounded-full overflow-hidden" style="background:var(--t-surface-raised)">
                            <div class="h-full rounded-full transition-all duration-500"
                                 [style.width]="sub.pct + '%'"
                                 [style.background]="sub.color"></div>
                          </div>
                        </div>
                      }
                    </div>
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && milestones().length === 0) {
        <div class="card text-center py-16 opacity-75">
          <div class="w-16 h-16 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center mx-auto mb-4">
            <span class="material-icons text-2xl" style="color:var(--t-text-secondary)">flag</span>
          </div>
          <h3 class="text-lg font-bold" style="color:var(--t-text-primary)">
            No milestones yet<span style="color:var(--t-accent)">.</span>
          </h3>
          <p class="text-sm mt-1 max-w-xs mx-auto" style="color:var(--t-text-secondary)">
            Define key deliverables and dates to track this initiative's progress.
          </p>
          <button class="btn-secondary text-xs mt-6" (click)="onOpenAddModal()">+ Add First Milestone</button>
        </div>
      }

      @if (!loading() && milestones().length > 0 && filteredMilestones().length === 0) {
        <div class="card text-center py-12">
          <p class="text-sm font-semibold" style="color:var(--t-text-secondary)">No milestones match the current filters.</p>
        </div>
      }
    </div>

    <!-- ADD MODAL -->
    @if (showAddModal()) {
      <div class="overlay animate-fade-in" (click)="onCloseAddModal()">
        <div class="modal-content card p-8 space-y-6 shadow-2xl" (click)="$event.stopPropagation()">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-bold">New Milestone<span class="text-[var(--t-accent)]">.</span></h2>
            <button class="btn-ghost p-1" (click)="onCloseAddModal()">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5" style="color:var(--t-text-secondary)">Milestone Name</label>
              <input type="text" [(ngModel)]="addForm.name" class="input-field" placeholder="e.g. Pilot Launch complete"/>
            </div>

            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5" style="color:var(--t-text-secondary)">Description</label>
              <textarea [(ngModel)]="addForm.description" rows="2" class="input-field" placeholder="Key outcomes or requirements..."></textarea>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5" style="color:var(--t-text-secondary)">Priority</label>
                <select [(ngModel)]="addForm.priority" class="input-field">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5" style="color:var(--t-text-secondary)">Target Completion</label>
                <input type="date" [(ngModel)]="addForm.planned_end" class="input-field"/>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t" style="border-color:var(--t-border)">
            <button class="btn-ghost" (click)="onCloseAddModal()">Cancel</button>
            <button class="btn-primary px-8" [disabled]="!addForm.name" (click)="onSaveMilestone()">Create Milestone</button>
          </div>
        </div>
      </div>
    }
  `,
})
export class MilestonesTabComponent implements OnInit {
  @Input() initiativeId = '';

  private readonly api = inject(ApiService);

  loading = signal(true);
  milestones = signal<MilestoneItem[]>([]);
  portfolioMilestones = signal<MilestoneItem[]>([]);
  expandedId = signal<string | null>(null);
  expandedDetail = signal<MilestoneDetail | null>(null);
  query = '';
  statusFilter = 'all';
  sortKey: 'manual' | 'due' | 'pressure' | 'priority' | 'name' = 'manual';
  checklistDraft = '';
  dependencyDraft = '';
  confirmDeleteId = signal<string | null>(null);

  // Add Modal State
  showAddModal = signal(false);
  addForm = {
    name: '',
    description: '',
    priority: 'medium',
    planned_end: ''
  };

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
    (globalThis as any).__transmuterMilestones = this;
    if (!this.initiativeId) { this.loading.set(false); return; }
    this.loadPortfolioMilestones();
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

  filteredMilestones(): MilestoneItem[] {
    const q = this.query.trim().toLowerCase();
    const priorityRank: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return this.milestones()
      .filter((ms) => this.statusFilter === 'all' || ms.status === this.statusFilter)
      .filter((ms) => {
        if (!q) return true;
        return `${ms.name} ${ms.description || ''} ${ms.owner_name || ''}`.toLowerCase().includes(q);
      })
      .sort((a, b) => {
        if (this.sortKey === 'due') return (a.planned_end || '9999-12-31').localeCompare(b.planned_end || '9999-12-31');
        if (this.sortKey === 'pressure') return parseFloat(b.pressure_score || '0') - parseFloat(a.pressure_score || '0');
        if (this.sortKey === 'priority') return (priorityRank[a.priority] ?? 9) - (priorityRank[b.priority] ?? 9);
        if (this.sortKey === 'name') return a.name.localeCompare(b.name);
        return (a.sort_order ?? 0) - (b.sort_order ?? 0) || (a.planned_end || '').localeCompare(b.planned_end || '');
      });
  }

  dependencyCandidates(currentId: string): MilestoneItem[] {
    const currentDeps = new Set((this.expandedDetail()?.dependencies || []).map((dep) => dep.upstream_milestone_id));
    const source = this.portfolioMilestones().length > 0 ? this.portfolioMilestones() : this.milestones();
    return source
      .filter((ms) => ms.id !== currentId && !currentDeps.has(ms.id))
      .sort((a, b) => {
        const initCompare = this.initiativeLabel(a).localeCompare(this.initiativeLabel(b));
        if (initCompare !== 0) return initCompare;
        return (a.planned_end || '9999-12-31').localeCompare(b.planned_end || '9999-12-31')
          || a.name.localeCompare(b.name);
      });
  }

  dependencyCandidateGroups(currentId: string): DependencyCandidateGroup[] {
    const groups = new Map<string, MilestoneItem[]>();
    for (const milestone of this.dependencyCandidates(currentId)) {
      const label = this.initiativeLabel(milestone);
      groups.set(label, [...(groups.get(label) || []), milestone]);
    }
    return Array.from(groups.entries()).map(([initiativeName, milestones]) => ({
      initiativeName,
      milestones,
    }));
  }

  dependencyCandidateLabel(candidate: MilestoneItem): string {
    const date = candidate.planned_end ? ` · ${candidate.planned_end}` : '';
    return `${candidate.name}${date}`;
  }

  // --- Modal Logic ---
  onOpenAddModal(): void {
    this.addForm = {
      name: '',
      description: '',
      priority: 'medium',
      planned_end: new Date().toISOString().slice(0, 10)
    };
    this.showAddModal.set(true);
  }

  onCloseAddModal(): void {
    this.showAddModal.set(false);
  }

  onSaveMilestone(): void {
    if (!this.addForm.name) return;
    
    this.api.post(`/initiatives/${this.initiativeId}/milestones`, {
      ...this.addForm,
      status: 'not_started'
    }).subscribe({
      next: () => {
        this.loadMilestones();
        this.onCloseAddModal();
      },
      error: () => alert('Failed to add milestone.')
    });
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

  addChecklistItem(milestoneId: string): void {
    const text = this.checklistDraft.trim();
    if (!text) return;
    const sortOrder = this.expandedDetail()?.checklist.length || 0;
    this.api.post<ChecklistItem>(`/milestones/${milestoneId}/checklist`, {
      text,
      sort_order: sortOrder,
    }).subscribe({
      next: () => {
        this.checklistDraft = '';
        this.refreshExpanded(milestoneId);
      },
      error: () => alert('Failed to add checklist item.'),
    });
  }

  deleteChecklistItem(milestoneId: string, itemId: string): void {
    this.api.delete(`/milestones/${milestoneId}/checklist/${itemId}`).subscribe({
      next: () => this.refreshExpanded(milestoneId),
      error: () => alert('Failed to delete checklist item.'),
    });
  }

  addDependency(milestoneId: string): void {
    if (!this.dependencyDraft) return;
    this.api.post<DependencyItem>(`/milestones/${milestoneId}/dependencies`, {
      upstream_milestone_id: this.dependencyDraft,
    }).subscribe({
      next: () => {
        this.dependencyDraft = '';
        this.refreshExpanded(milestoneId);
      },
      error: () => alert('Failed to add dependency. Check for circular dependencies.'),
    });
  }

  deleteDependency(milestoneId: string, dependencyId: string): void {
    this.api.delete(`/milestones/${milestoneId}/dependencies/${dependencyId}`).subscribe({
      next: () => this.refreshExpanded(milestoneId),
      error: () => alert('Failed to remove dependency.'),
    });
  }

  updateMilestone(milestoneId: string, patch: Partial<MilestoneItem>): void {
    this.api.put<MilestoneDetail>(`/milestones/${milestoneId}`, patch).subscribe({
      next: () => this.refreshExpanded(milestoneId),
      error: () => alert('Failed to update milestone.'),
    });
  }

  deleteMilestone(milestoneId: string): void {
    this.api.delete(`/milestones/${milestoneId}`).subscribe({
      next: () => {
        this.confirmDeleteId.set(null);
        this.expandedId.set(null);
        this.expandedDetail.set(null);
        this.loadMilestones();
      },
      error: () => {
        this.confirmDeleteId.set(null);
        alert('Failed to delete milestone.');
      },
    });
  }

  moveMilestone(ms: MilestoneItem, direction: -1 | 1): void {
    if (this.sortKey !== 'manual') return;
    const ordered = [...this.milestones()].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    const index = ordered.findIndex((item) => item.id === ms.id);
    const target = ordered[index + direction];
    if (index < 0 || !target) return;
    const currentOrder = ms.sort_order ?? index * 10;
    const targetOrder = target.sort_order ?? (index + direction) * 10;
    this.api.put(`/milestones/${ms.id}`, { sort_order: targetOrder }).subscribe({
      next: () => {
        this.api.put(`/milestones/${target.id}`, { sort_order: currentOrder }).subscribe({
          next: () => this.loadMilestones(),
          error: () => this.loadMilestones(),
        });
      },
      error: () => alert('Failed to reorder milestone.'),
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
        this.milestones.set(r.items.map((item, index) => ({
          ...item,
          sort_order: item.sort_order ?? index * 10,
        })));
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadPortfolioMilestones(): void {
    this.api.get<{ items: MilestoneItem[]; total: number }>('/milestones').subscribe({
      next: (r: { items: MilestoneItem[] }) => {
        this.portfolioMilestones.set(r.items || []);
      },
      error: () => this.portfolioMilestones.set([]),
    });
  }

  private loadDetail(id: string): void {
    this.api.get<MilestoneDetail>(`/milestones/${id}`).subscribe({
      next: (d: MilestoneDetail) => this.expandedDetail.set(d),
      error: () => this.expandedDetail.set(null),
    });
  }

  private refreshExpanded(milestoneId: string): void {
    this.loadMilestones();
    this.loadPortfolioMilestones();
    this.loadDetail(milestoneId);
  }

  private initiativeLabel(milestone: MilestoneItem): string {
    return milestone.initiative_name || (
      milestone.initiative_id === this.initiativeId ? 'This Initiative' : 'Unassigned Initiative'
    );
  }
}
