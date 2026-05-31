import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

interface RoadmapMilestone {
  id: string;
  initiative_id: string;
  name: string;
  initiative_name: string | null;
  planned_end: string | null;
  status: string;
  pressure_score: string;
  pressure_level?: string | null;
  priority?: string | null;
}

interface InitiativeGroup {
  name: string;
  milestones: RoadmapMilestone[];
}

interface DependencyEdge {
  id: string;
  source: string;
  target: string;
  status: 'blocking' | 'at_risk' | 'resolved' | 'on_track';
}

interface RoadmapLink {
  id: string;
  sourceId: string;
  targetId: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  path: string;
  status: DependencyEdge['status'];
}

interface DependencyItem {
  id: string;
  upstream: { id: string; name: string; initiative_code?: string | null };
  downstream: { id: string; name: string; initiative_code?: string | null };
  status: DependencyEdge['status'];
  upstream_status?: string | null;
  upstream_planned_end?: string | null;
  upstream_pressure_score?: string | null;
  downstream_status?: string | null;
}

interface NeighborMilestone {
  label: string;
  milestone: RoadmapMilestone | null;
}

@Component({
  selector: 'app-roadmap',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Roadmap Explorer<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Timeline view of all portfolio milestones across initiatives.</p>
        </div>
        <div class="flex gap-3">
          <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <a routerLink="/progress" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Milestones</a>
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Roadmap</button>
             <a routerLink="/progress/action-items" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Action Items</a>
          </div>
          <select [ngModel]="timeframe()" (ngModelChange)="timeframe.set(+$event)" class="input-field text-xs h-9 w-32">
            <option value="6">6 Months</option>
            <option value="12">12 Months</option>
            <option value="24">24 Months</option>
          </select>
        </div>
      </div>

      <!-- Timeline Container -->
      <div class="card overflow-x-auto">
        <div class="min-w-[1200px] p-6">
          
          <!-- Timeline Header (Months) -->
          <div class="grid grid-cols-[250px_1fr] border-b border-[var(--t-border)] mb-4">
            <div class="py-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative</div>
            <div class="flex">
              @for (month of months(); track month.label) {
                <div class="flex-1 text-center py-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] border-l border-[var(--t-border)]/30">
                  {{ month.label }}
                </div>
              }
            </div>
          </div>

          <!-- Timeline Rows -->
          <div class="relative" [style.minHeight.px]="timelineHeight()">
            <svg class="absolute top-0 bottom-0 left-[250px] right-0 w-[calc(100%-250px)] pointer-events-none z-10"
                 [attr.height]="timelineHeight()"
                 [attr.viewBox]="'0 0 100 ' + timelineHeight()"
                 preserveAspectRatio="none"
                 aria-hidden="true">
              <defs>
                <marker id="roadmap-arrow-on_track" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--t-accent)"></path>
                </marker>
                <marker id="roadmap-arrow-blocking" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--t-red)"></path>
                </marker>
                <marker id="roadmap-arrow-at_risk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--t-amber)"></path>
                </marker>
                <marker id="roadmap-arrow-resolved" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--t-text-tertiary)"></path>
                </marker>
              </defs>
              @for (link of visibleLinks(); track link.id) {
                <path [attr.d]="link.path"
                      fill="none"
                      stroke-linecap="round"
                      stroke-dasharray="3 4"
                      vector-effect="non-scaling-stroke"
                      [attr.marker-end]="dependencyMarkerUrl(link.status)"
                      [attr.stroke]="dependencyStatusColor(link.status)"
                      [attr.stroke-width]="dependencyStrokeWidth(link.status)"
                      [attr.opacity]="dependencyOpacity(link.status)">
                  <title>{{ dependencyTitle(link) }}</title>
                </path>
              }
            </svg>

            @for (group of groupedMilestones(); track group.name; let rowIndex = $index) {
              <div class="grid grid-cols-[250px_1fr] group border-b last:border-b-0"
                   style="border-color:var(--t-border)"
                   [style.height.px]="rowHeight">
                <!-- Initiative Label -->
                <div class="pr-4 py-3">
                  <h3 class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors truncate" [title]="group.name">
                    {{ group.name }}
                  </h3>
                  <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ group.milestones.length }} milestones</p>
                </div>

                <!-- Milestone Lane -->
                <div class="relative h-full flex items-center">
                  <!-- Grid Background Lines -->
                  <div class="absolute inset-0 flex pointer-events-none">
                    @for (month of months(); track month.label) {
                      <div class="flex-1 border-l border-[var(--t-border)]/30 h-full"></div>
                    }
                  </div>

                  <!-- Milestones -->
                  @for (m of group.milestones; track m.id) {
                    @if (getMilestonePosition(m.planned_end) !== null) {
                      <div class="absolute group/ms" 
                           [style.left.%]="getMilestonePosition(m.planned_end)"
                           [title]="m.name + ' (' + (m.planned_end | date:'mediumDate') + ')'">
                        <!-- Dot -->
                        <button type="button"
                                class="w-4 h-4 rounded-full border-2 border-[var(--t-surface)] shadow-sm transition-transform group-hover/ms:scale-125 cursor-pointer relative z-20 focus:outline-none focus:ring-2 focus:ring-[var(--t-accent)]"
                                [class]="getMilestoneStatusClass(m)"
                                [style.background]="getMilestoneColor(m)"
                                [style.boxShadow]="dependencyMilestoneIds().has(m.id) ? dependencyMarkerShadow(m) : ''"
                                [attr.aria-label]="'Open milestone detail for ' + m.name"
                                [attr.data-testid]="'roadmap-milestone-' + m.id"
                                (click)="openMilestone(m)"></button>
                        
                        <!-- Tooltip-style Label -->
                        <div class="absolute top-4 left-1/2 -translate-x-1/2 opacity-0 group-hover/ms:opacity-100 pointer-events-none transition-opacity z-10">
                          <div class="bg-[var(--t-surface-raised)] border border-[var(--t-border)] rounded px-2 py-1 shadow-lg whitespace-nowrap">
                            <p class="text-[10px] font-bold text-[var(--t-text-primary)]">{{ m.name }}</p>
                            <p class="text-[9px] text-[var(--t-text-tertiary)]">{{ m.planned_end | date:'MMM d, y' }}</p>
                          </div>
                        </div>
                      </div>
                    }
                  }
                </div>
              </div>
            }

            @if (groupedMilestones().length === 0) {
              <div class="py-12 text-center text-xs text-[var(--t-text-tertiary)]">
                No milestones found in this timeframe.
              </div>
            }
          </div>

        </div>
      </div>

      <!-- Legend -->
      <div class="flex items-center gap-6 text-[10px] font-medium text-[var(--t-text-tertiary)] uppercase tracking-widest px-2">
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-green)]"></span> On Track</span>
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-amber)]"></span> At Risk</span>
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-red)]"></span> Due / Blocking</span>
        <span class="flex items-center gap-1.5"><span class="inline-block w-6 border-t-2 border-dotted border-[var(--t-accent)]"></span> Dependency Link</span>
        @if (hiddenDependencyCount() > 0) {
          <span class="ml-auto">{{ hiddenDependencyCount() }} links hidden by timeframe</span>
        } @else {
          <span class="ml-auto">Markers indicate planned completion dates</span>
        }
      </div>

      @if (selectedMilestone(); as selected) {
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6"
             (click)="closeMilestone()"
             data-testid="roadmap-milestone-modal">
          <div class="card w-full max-w-5xl max-h-[88vh] overflow-hidden shadow-2xl"
               style="background:var(--t-surface)"
               (click)="$event.stopPropagation()">
            <div class="px-6 py-5 border-b border-[var(--t-border)] flex items-start justify-between gap-6">
              <div class="min-w-0">
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
                  {{ selected.initiative_name || 'Unassigned Initiative' }}
                </p>
                <h2 class="mt-1 text-2xl font-black text-[var(--t-text-primary)] truncate">{{ selected.name }}</h2>
                <div class="mt-3 flex flex-wrap gap-2 text-[10px] font-black uppercase">
                  <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">{{ selected.status.replace('_', ' ') }}</span>
                  <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">{{ selected.planned_end || 'No due date' }}</span>
                  <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">Pressure {{ selected.pressure_score || '0' }}</span>
                </div>
              </div>
              <button type="button" class="btn-ghost h-9 w-9 p-0" aria-label="Close milestone detail" (click)="closeMilestone()">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>

            <div class="p-6 overflow-y-auto max-h-[calc(88vh-96px)] grid grid-cols-1 xl:grid-cols-3 gap-6">
              <section class="xl:col-span-2 space-y-5">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @for (neighbor of milestoneNeighbors(selected); track neighbor.label) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                      <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ neighbor.label }}</p>
                      @if (neighbor.milestone) {
                        <p class="mt-2 text-sm font-black text-[var(--t-text-primary)]">{{ neighbor.milestone.name }}</p>
                        <p class="mt-1 text-[11px] text-[var(--t-text-secondary)]">{{ neighbor.milestone.planned_end || 'No due date' }}</p>
                      } @else {
                        <p class="mt-2 text-sm text-[var(--t-text-secondary)]">None in this initiative.</p>
                      }
                    </div>
                  }
                </div>

                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5" data-testid="roadmap-upstream-dependencies">
                  <div class="flex items-center justify-between">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Upstream Dependencies</h3>
                    <span class="text-[10px] font-black text-[var(--t-text-tertiary)]">{{ upstreamDependencies(selected.id).length }} blockers</span>
                  </div>
                  <div class="mt-4 space-y-3">
                    @for (dep of upstreamDependencies(selected.id); track dep.id) {
                      <div class="flex items-center justify-between gap-4 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                        <div class="min-w-0">
                          <p class="text-xs font-black text-[var(--t-text-primary)] truncate">{{ dep.upstream.name }}</p>
                          <p class="text-[10px] font-bold uppercase text-[var(--t-accent)]">{{ dep.upstream.initiative_code || 'GEN' }}</p>
                        </div>
                        <span class="text-[10px] font-black uppercase" [style.color]="dependencyStatusColor(dep.status)">{{ dep.status.replace('_', ' ') }}</span>
                      </div>
                    }
                    @if (upstreamDependencies(selected.id).length === 0) {
                      <p class="text-xs text-[var(--t-text-secondary)] border border-dashed border-[var(--t-border)] p-4">No upstream blockers linked.</p>
                    }
                  </div>
                </div>
              </section>

              <section class="space-y-5">
                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5" data-testid="roadmap-downstream-dependencies">
                  <div class="flex items-center justify-between">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Downstream Dependencies</h3>
                    <span class="text-[10px] font-black text-[var(--t-text-tertiary)]">{{ downstreamDependencies(selected.id).length }} dependents</span>
                  </div>
                  <div class="mt-4 space-y-3">
                    @for (dep of downstreamDependencies(selected.id); track dep.id) {
                      <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                        <div class="flex items-start justify-between gap-3">
                          <div class="min-w-0">
                            <p class="text-xs font-black text-[var(--t-text-primary)] truncate">{{ dep.downstream.name }}</p>
                            <p class="text-[10px] font-bold uppercase text-[var(--t-accent)]">{{ dep.downstream.initiative_code || 'GEN' }}</p>
                          </div>
                          <span class="text-[10px] font-black uppercase" [style.color]="dependencyStatusColor(dep.status)">{{ dep.status.replace('_', ' ') }}</span>
                        </div>
                      </div>
                    }
                    @if (downstreamDependencies(selected.id).length === 0) {
                      <p class="text-xs text-[var(--t-text-secondary)] border border-dashed border-[var(--t-border)] p-4">No downstream milestones depend on this one.</p>
                    }
                  </div>
                </div>

                <a [routerLink]="['/initiatives', selected.initiative_id]"
                   class="btn-secondary w-full justify-center text-xs"
                   (click)="closeMilestone()">
                  Open Initiative
                </a>
              </section>
            </div>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    :host { display: block; }
    .animate-fade-in { animation: fade-in 0.4s ease-out; }
    @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  `]
})
export class RoadmapComponent implements OnInit {
  private readonly api = inject(ApiService);
  readonly rowHeight = 72;
  
  milestones = signal<RoadmapMilestone[]>([]);
  dependencies = signal<DependencyEdge[]>([]);
  dependencyItems = signal<DependencyItem[]>([]);
  selectedMilestone = signal<RoadmapMilestone | null>(null);
  timeframe = signal(12); // months

  months = computed(() => {
    const months = [];
    const now = new Date();
    // Start from 1 month ago to show context
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    
    for (let i = 0; i < this.timeframe(); i++) {
      const d = new Date(start.getFullYear(), start.getMonth() + i, 1);
      months.push({
        date: d,
        label: d.toLocaleString('default', { month: 'short', year: '2-digit' })
      });
    }
    return months;
  });

  groupedMilestones = computed(() => {
    const groups: { [key: string]: RoadmapMilestone[] } = {};
    const timelineStart = this.months()[0].date;
    const timelineEnd = new Date(this.months()[this.months().length - 1].date);
    timelineEnd.setMonth(timelineEnd.getMonth() + 1);

    this.milestones().forEach(m => {
      if (!m.planned_end) return;
      const d = new Date(m.planned_end);
      if (d >= timelineStart && d <= timelineEnd) {
        const iName = m.initiative_name || 'Unassigned Initiative';
        if (!groups[iName]) groups[iName] = [];
        groups[iName].push(m);
      }
    });

    return Object.keys(groups).sort().map(name => ({
      name,
      milestones: groups[name].sort((a, b) => 
        new Date(a.planned_end || '9999-12-31').getTime() - new Date(b.planned_end || '9999-12-31').getTime()
      )
    }));
  });

  visibleMilestonePositions = computed(() => {
    const positions = new Map<string, { x: number; y: number; milestone: RoadmapMilestone; group: string }>();
    this.groupedMilestones().forEach((group, rowIndex) => {
      group.milestones.forEach((milestone) => {
        const x = this.getMilestonePosition(milestone.planned_end);
        if (x === null) return;
        positions.set(milestone.id, {
          x,
          y: rowIndex * this.rowHeight + this.rowHeight / 2,
          milestone,
          group: group.name,
        });
      });
    });
    return positions;
  });

  visibleLinks = computed(() => {
    const positions = this.visibleMilestonePositions();
    return this.dependencies()
      .map((edge): RoadmapLink | null => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) return null;
        return {
          id: edge.id,
          sourceId: edge.source,
          targetId: edge.target,
          sourceX: source.x,
          sourceY: source.y,
          targetX: target.x,
          targetY: target.y,
          path: this.dependencyPath(source.x, source.y, target.x, target.y),
          status: edge.status,
        };
      })
      .filter((link): link is RoadmapLink => !!link);
  });

  hiddenDependencyCount = computed(() => this.dependencies().length - this.visibleLinks().length);

  dependencyMilestoneIds = computed(() => {
    const ids = new Set<string>();
    this.visibleLinks().forEach((link) => {
      ids.add(link.sourceId);
      ids.add(link.targetId);
    });
    return ids;
  });

  ngOnInit() {
    this.api.get<any>('/milestones').subscribe(res => {
      this.milestones.set(res.items || []);
    });
    this.api.get<{ edges: DependencyEdge[]; items: DependencyItem[] }>('/dependencies').subscribe({
      next: (res) => {
        this.dependencies.set(res.edges || []);
        this.dependencyItems.set(res.items || []);
      },
      error: () => {
        this.dependencies.set([]);
        this.dependencyItems.set([]);
      },
    });
  }

  openMilestone(milestone: RoadmapMilestone): void {
    this.selectedMilestone.set(milestone);
  }

  closeMilestone(): void {
    this.selectedMilestone.set(null);
  }

  upstreamDependencies(milestoneId: string): DependencyItem[] {
    return this.dependencyItems().filter((dependency) => dependency.downstream?.id === milestoneId);
  }

  downstreamDependencies(milestoneId: string): DependencyItem[] {
    return this.dependencyItems().filter((dependency) => dependency.upstream?.id === milestoneId);
  }

  milestoneNeighbors(selected: RoadmapMilestone): NeighborMilestone[] {
    const initiativeMilestones = this.milestones()
      .filter((milestone) => milestone.initiative_id === selected.initiative_id && !!milestone.planned_end)
      .sort((a, b) => {
        const dateDelta = new Date(a.planned_end || '9999-12-31').getTime() - new Date(b.planned_end || '9999-12-31').getTime();
        return dateDelta || a.name.localeCompare(b.name);
      });
    const index = initiativeMilestones.findIndex((milestone) => milestone.id === selected.id);
    return [
      { label: 'Previous Due', milestone: index > 0 ? initiativeMilestones[index - 1] : null },
      { label: 'Next Due', milestone: index >= 0 && index < initiativeMilestones.length - 1 ? initiativeMilestones[index + 1] : null },
    ];
  }

  timelineHeight(): number {
    return Math.max(this.groupedMilestones().length * this.rowHeight, 48);
  }

  getMilestonePosition(dateStr: string | null): number | null {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return null;
    const start = this.months()[0].date;
    const end = new Date(this.months()[this.months().length - 1].date);
    end.setMonth(end.getMonth() + 1);

    const totalMs = end.getTime() - start.getTime();
    const currentMs = date.getTime() - start.getTime();
    
    return Math.max(0, Math.min(100, (currentMs / totalMs) * 100));
  }

  dependencyStatusColor(status: DependencyEdge['status']): string {
    switch (status) {
      case 'blocking': return 'var(--t-red)';
      case 'at_risk': return 'var(--t-amber)';
      case 'resolved': return 'var(--t-text-tertiary)';
      default: return 'var(--t-accent)';
    }
  }

  dependencyStrokeWidth(status: DependencyEdge['status']): number {
    return status === 'blocking' ? 2.2 : 1.6;
  }

  dependencyOpacity(status: DependencyEdge['status']): number {
    return status === 'resolved' ? 0.45 : 0.82;
  }

  dependencyMarkerUrl(status: DependencyEdge['status']): string {
    return `url(#roadmap-arrow-${status})`;
  }

  dependencyMarkerShadow(milestone: RoadmapMilestone): string {
    return `0 0 0 3px var(--t-surface), 0 0 0 5px ${this.getMilestoneColor(milestone)}`;
  }

  dependencyTitle(link: RoadmapLink): string {
    const positions = this.visibleMilestonePositions();
    const source = positions.get(link.sourceId)?.milestone.name || 'Upstream milestone';
    const target = positions.get(link.targetId)?.milestone.name || 'Downstream milestone';
    return `${source} blocks ${target}`;
  }

  private dependencyPath(sourceX: number, sourceY: number, targetX: number, targetY: number): string {
    const distance = Math.abs(targetX - sourceX);
    const bend = Math.max(4, Math.min(14, distance / 2));
    const sourceBend = sourceX <= targetX ? sourceX + bend : sourceX - bend;
    const targetBend = sourceX <= targetX ? targetX - bend : targetX + bend;
    return `M ${sourceX} ${sourceY} C ${sourceBend} ${sourceY}, ${targetBend} ${targetY}, ${targetX} ${targetY}`;
  }

  getMilestoneStatusClass(milestone: RoadmapMilestone): string {
    if (this.isComplete(milestone)) return 'opacity-60 grayscale-[0.5]';
    if (this.isDue(milestone) || this.hasBlockingDependency(milestone.id)) {
      return 'ring-2 ring-[var(--t-red)] ring-offset-2 ring-offset-[var(--t-surface)]';
    }
    if (this.isMilestoneAtRisk(milestone)) {
      return 'ring-2 ring-[var(--t-amber)] ring-offset-2 ring-offset-[var(--t-surface)]';
    }
    return '';
  }

  getMilestoneColor(milestone: RoadmapMilestone): string {
    if (this.isComplete(milestone)) return 'var(--t-text-tertiary)';
    if (this.isDue(milestone) || this.hasBlockingDependency(milestone.id)) return 'var(--t-red)';
    if (this.isMilestoneAtRisk(milestone)) return 'var(--t-amber)';
    return 'var(--t-green)';
  }

  private isComplete(milestone: RoadmapMilestone): boolean {
    return ['complete', 'completed', 'done'].includes((milestone.status || '').toLowerCase());
  }

  private isDue(milestone: RoadmapMilestone): boolean {
    if (!milestone.planned_end || this.isComplete(milestone)) return false;
    return milestone.planned_end <= new Date().toISOString().slice(0, 10);
  }

  private isMilestoneAtRisk(milestone: RoadmapMilestone): boolean {
    if (this.isComplete(milestone)) return false;
    const status = (milestone.status || '').toLowerCase();
    const pressureLevel = (milestone.pressure_level || '').toLowerCase();
    const priority = (milestone.priority || '').toLowerCase();
    const pressureScore = Number(milestone.pressure_score) || 0;
    return ['at_risk', 'at-risk', 'delayed'].includes(status)
      || ['at_risk', 'at-risk', 'medium', 'high'].includes(pressureLevel)
      || ['high', 'critical'].includes(priority)
      || pressureScore >= 3.4
      || this.relatedDependencies(milestone.id).some((dependency) => dependency.status === 'at_risk');
  }

  private hasBlockingDependency(milestoneId: string): boolean {
    return this.relatedDependencies(milestoneId).some((dependency) => dependency.status === 'blocking');
  }

  private relatedDependencies(milestoneId: string): DependencyItem[] {
    return this.dependencyItems().filter(
      (dependency) => dependency.upstream?.id === milestoneId || dependency.downstream?.id === milestoneId,
    );
  }
}
