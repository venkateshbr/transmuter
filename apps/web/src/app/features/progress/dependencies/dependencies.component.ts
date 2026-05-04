import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dependencies',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Connection Graph<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Intelligent mapping of cross-initiative milestone dependencies and critical path inhibitors.</p>
        </div>
        <div class="flex gap-3 items-center">
          <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <a routerLink="/progress" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Milestones</a>
             <a routerLink="/progress/roadmap" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Roadmap</a>
             <a routerLink="/progress/action-items" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Action Items</a>
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Dependencies</button>
          </div>
          <button class="btn-primary text-sm h-9 flex items-center gap-2 px-6">
            <span class="material-icons text-sm">link</span>
            Link Nodes
          </button>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="dependency-stats">
        @for (card of statsCards(); track card.label) {
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-wider mb-2" style="color:var(--t-text-secondary)">{{ card.label }}</p>
            <p class="text-2xl font-black" [style.color]="card.color">{{ card.value }}</p>
          </div>
        }
      </div>

      <div class="card p-6" data-testid="dependency-graph">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-base font-bold text-[var(--t-text-primary)]">Dependency Graph<span class="text-[var(--t-accent)]">.</span></h3>
          <span class="badge-ghost text-[10px] uppercase font-bold">{{ nodes().length }} nodes / {{ dependencies().length }} edges</span>
        </div>
        @if (nodes().length) {
          <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            @for (node of nodes(); track node.id) {
              <div class="rounded-lg border bg-[var(--t-surface-raised)] p-3" style="border-color:var(--t-border)">
                <div class="flex items-center justify-between gap-3">
                  <p class="text-sm font-bold truncate text-[var(--t-text-primary)]">{{ node.name }}</p>
                  <span class="text-[9px] font-black uppercase text-[var(--t-accent)]">{{ node.initiative_code || 'GEN' }}</span>
                </div>
                <p class="text-[10px] font-semibold uppercase mt-1" style="color:var(--t-text-secondary)">{{ downstreamCount(node.id) }} downstream / {{ upstreamCount(node.id) }} upstream</p>
              </div>
            }
          </div>
        } @else {
          <div class="h-28 flex items-center justify-center text-sm" style="color:var(--t-text-secondary)">No dependency nodes available.</div>
        }
      </div>

      <!-- Dependency Matrix / Grid -->
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
        @for (d of dependencies(); track d.id) {
          <div class="card p-0 overflow-hidden hover:border-[var(--t-accent)] transition-all group shadow-xl hover:shadow-blue-900/5">
            <div class="flex h-full">
              <!-- Upstream Panel -->
              <div class="flex-1 p-6 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)] border-r border-[var(--t-border)]">
                <div class="flex items-center gap-2 mb-4">
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
                  <p class="text-[9px] font-black uppercase tracking-widest text-blue-500">Upstream Node</p>
                </div>
                <h4 class="text-sm font-black text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors line-clamp-2 leading-tight h-10">
                  {{ d.upstream?.name }}
                </h4>
                <div class="mt-4 flex items-center gap-2">
                   <div class="w-6 h-6 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[8px] font-black text-[var(--t-accent)]">
                     {{ d.upstream?.initiative_code?.substring(0,2) }}
                   </div>
                   <p class="text-[9px] font-bold text-[var(--t-text-secondary)] uppercase">{{ d.upstream?.initiative_code }}</p>
                </div>
                <div class="mt-4 pt-4 border-t border-[var(--t-border)]/50">
                   <span class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-tighter">Status: </span>
                   <span class="text-[9px] font-black uppercase" [class]="getStatusClass(d.status)">
                     {{ d.status.replace('_', ' ') }}
                   </span>
                </div>
              </div>

              <!-- Flow Visual -->
              <div class="w-16 flex flex-col items-center justify-center bg-[var(--t-surface-raised)]/30 relative">
                 <div class="absolute inset-y-0 w-px bg-gradient-to-b from-transparent via-[var(--t-accent)]/30 to-transparent"></div>
                 <div class="z-10 w-8 h-8 rounded-full bg-[var(--t-surface)] border border-[var(--t-border)] flex items-center justify-center text-[var(--t-accent)] shadow-sm group-hover:scale-125 transition-transform group-hover:bg-[var(--t-accent)] group-hover:text-white">
                   <span class="material-icons text-sm">trending_flat</span>
                 </div>
                 <p class="text-[7px] font-black text-[var(--t-text-tertiary)] uppercase mt-3 tracking-widest">Blocks</p>
              </div>

              <!-- Downstream Panel -->
              <div class="flex-1 p-6">
                <div class="flex items-center gap-2 mb-4 justify-end">
                  <p class="text-[9px] font-black uppercase tracking-widest text-red-500">Dependent Node</p>
                  <span class="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"></span>
                </div>
                <h4 class="text-sm font-black text-[var(--t-text-primary)] text-right group-hover:text-[var(--t-accent)] transition-colors line-clamp-2 leading-tight h-10">
                  {{ d.downstream?.name }}
                </h4>
                <div class="mt-4 flex items-center gap-2 justify-end">
                   <p class="text-[9px] font-bold text-[var(--t-text-secondary)] uppercase">{{ d.downstream?.initiative_code }}</p>
                   <div class="w-6 h-6 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[8px] font-black text-[var(--t-accent)]">
                     {{ d.downstream?.initiative_code?.substring(0,2) }}
                   </div>
                </div>
                <div class="mt-4 pt-4 border-t border-[var(--t-border)]/50 text-right">
                   <span class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-tighter">Impact: </span>
                   <span class="text-[9px] font-black uppercase" [class]="getStatusClass(d.status)">
                     {{ getImpactLabel(d.status) }}
                   </span>
                </div>
              </div>
            </div>
          </div>
        }

        @if (dependencies().length === 0) {
          <!-- Empty State with stylized connector -->
          <div class="col-span-2 py-32 flex flex-col items-center justify-center text-center">
             <div class="w-24 h-24 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center mb-6 relative">
                <span class="material-icons text-3xl text-[var(--t-text-tertiary)]">hub</span>
                <div class="absolute inset-0 rounded-full border-2 border-dashed border-[var(--t-border)] animate-spin-slow"></div>
             </div>
             <h3 class="text-lg font-black text-[var(--t-text-primary)] uppercase tracking-widest">No Active Connections</h3>
             <p class="text-xs text-[var(--t-text-secondary)] mt-2 max-w-xs mx-auto">
               Cross-initiative dependencies will appear here once you link milestones between workstreams.
             </p>
             <button class="btn-primary mt-8 px-8 rounded-2xl shadow-xl shadow-blue-900/10">Initialize Mapping</button>
          </div>
        }
      </div>

      <div class="card overflow-hidden" data-testid="dependency-table">
        <div class="px-6 py-4 border-b border-[var(--t-border)]">
          <h3 class="text-base font-bold text-[var(--t-text-primary)]">Cross-Milestone Dependency Table<span class="text-[var(--t-accent)]">.</span></h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-wider" style="color:var(--t-text-secondary)">
              <tr>
                <th class="text-left px-6 py-3">Upstream</th>
                <th class="text-left px-6 py-3">Downstream</th>
                <th class="text-left px-6 py-3">Status</th>
                <th class="text-left px-6 py-3">Upstream Due</th>
                <th class="text-left px-6 py-3">Pressure</th>
              </tr>
            </thead>
            <tbody>
              @for (d of dependencies(); track d.id) {
                <tr class="border-t border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-colors">
                  <td class="px-6 py-4 font-bold text-[var(--t-text-primary)]">{{ d.upstream?.name }} <span class="text-[10px] text-[var(--t-accent)]">{{ d.upstream?.initiative_code }}</span></td>
                  <td class="px-6 py-4 text-[var(--t-text-primary)]">{{ d.downstream?.name }} <span class="text-[10px] text-[var(--t-accent)]">{{ d.downstream?.initiative_code }}</span></td>
                  <td class="px-6 py-4"><span class="text-[10px] font-black uppercase" [class]="getStatusClass(d.status)">{{ d.status.replace('_', ' ') }}</span></td>
                  <td class="px-6 py-4 text-[var(--t-text-secondary)]">{{ d.upstream_planned_end | date:'MMM d, y' }}</td>
                  <td class="px-6 py-4 text-[var(--t-text-secondary)]">{{ d.upstream_pressure_score || '0' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class DependenciesComponent implements OnInit {
  private readonly api = inject(ApiService);
  dependencies = signal<any[]>([]);
  stats = signal<any>({ total: 0, blocking: 0, at_risk: 0, resolved: 0, on_track: 0 });
  nodes = signal<any[]>([]);
  edges = signal<any[]>([]);

  ngOnInit() {
    this.api.get<any>('/portfolio/dependencies').subscribe(res => {
      this.dependencies.set(res.items || []);
      this.stats.set(res.stats || { total: 0, blocking: 0, at_risk: 0, resolved: 0, on_track: 0 });
      this.nodes.set(res.nodes || []);
      this.edges.set(res.edges || []);
    });
  }

  statsCards() {
    const s = this.stats();
    return [
      { label: 'Total', value: s.total || 0, color: 'var(--t-text-primary)' },
      { label: 'Blocking', value: s.blocking || 0, color: 'var(--t-red)' },
      { label: 'At Risk', value: s.at_risk || 0, color: 'var(--t-amber)' },
      { label: 'Resolved', value: s.resolved || 0, color: 'var(--t-green)' },
    ];
  }

  downstreamCount(nodeId: string): number {
    return this.edges().filter(edge => edge.source === nodeId).length;
  }

  upstreamCount(nodeId: string): number {
    return this.edges().filter(edge => edge.target === nodeId).length;
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'blocking': return 'text-red-500';
      case 'at_risk': return 'text-amber-500';
      case 'resolved': return 'text-emerald-500';
      default: return 'text-[var(--t-accent)]';
    }
  }

  getImpactLabel(status: string): string {
    switch (status) {
      case 'blocking': return 'Critical block';
      case 'at_risk': return 'Pressure risk';
      case 'resolved': return 'Resolved';
      default: return 'Tracked';
    }
  }
}
