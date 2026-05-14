import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-dependencies-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="space-y-5">
      <div class="grid gap-4 md:grid-cols-5">
        @for (card of statsCards(); track card.label) {
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
            <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ card.value }}</p>
          </div>
        }
      </div>

      <div class="card p-5">
        <div class="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Link Dependency</h2>
            <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Create an initiative-level dependency edge</p>
          </div>
          <button type="button" class="btn-primary text-[10px]" (click)="createDependency()" [disabled]="creating()" aria-label="Create initiative dependency">
            {{ creating() ? 'Saving' : 'Create Link' }}
          </button>
        </div>
        <div class="grid gap-3 md:grid-cols-6">
          <select class="input-field md:col-span-2" [(ngModel)]="draft.upstream_initiative_id" aria-label="Upstream initiative">
            @for (initiative of initiatives(); track initiative.id) {
              <option [value]="initiative.id">{{ initiative.initiative_code }} · {{ initiative.name }}</option>
            }
          </select>
          <select class="input-field md:col-span-2" [(ngModel)]="draft.downstream_initiative_id" aria-label="Downstream initiative">
            @for (initiative of initiatives(); track initiative.id) {
              <option [value]="initiative.id">{{ initiative.initiative_code }} · {{ initiative.name }}</option>
            }
          </select>
          <select class="input-field" [(ngModel)]="draft.dependency_type" aria-label="Dependency type">
            <option value="blocks">Blocks</option>
            <option value="enables">Enables</option>
            <option value="informs">Informs</option>
            <option value="duplicates">Duplicates</option>
            <option value="requires_decision">Requires decision</option>
          </select>
          <select class="input-field" [(ngModel)]="draft.severity" aria-label="Dependency severity">
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div class="mt-3 grid gap-3 md:grid-cols-[160px_1fr]">
          <input class="input-field" type="date" [(ngModel)]="draft.due_date" aria-label="Dependency due date">
          <input class="input-field" [(ngModel)]="draft.resolution_notes" placeholder="Resolution notes" aria-label="Dependency resolution notes">
        </div>
        @if (error()) {
          <p class="mt-3 text-xs font-bold text-red-500">{{ error() }}</p>
        }
      </div>

      <div class="card overflow-hidden">
        <div class="border-b border-[var(--t-border)] p-5">
          <h2 class="text-base font-black text-[var(--t-text-primary)]">Initiative Dependencies</h2>
          <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Upstream blockers and downstream blast radius</p>
        </div>
        <div class="divide-y divide-[var(--t-border)]">
          @for (dep of dependencies(); track dep.id) {
            <div class="grid gap-4 p-5 md:grid-cols-[1fr_120px_1fr_140px] md:items-center">
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Upstream</p>
                <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ dep.upstream?.initiative_code }} · {{ dep.upstream?.name }}</p>
              </div>
              <div class="text-center text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
                {{ dep.dependency_type?.replace('_', ' ') }}
              </div>
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Downstream</p>
                <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ dep.downstream?.initiative_code }} · {{ dep.downstream?.name }}</p>
              </div>
              <div class="text-right">
                <p class="text-[10px] font-black uppercase" [class.text-red-500]="dep.status === 'blocking'" [class.text-amber-500]="dep.status === 'at_risk'" [class.text-[var(--t-accent)]]="dep.status !== 'blocking' && dep.status !== 'at_risk'">{{ dep.status?.replace('_', ' ') }}</p>
                <p class="mt-1 text-[10px] font-bold text-[var(--t-text-tertiary)]">Blast {{ dep.blast_radius || 0 }}</p>
              </div>
            </div>
          } @empty {
            <div class="p-8 text-sm text-[var(--t-text-secondary)]">No initiative-level dependencies linked yet.</div>
          }
        </div>
      </div>
    </section>
  `,
})
export class DependenciesTabComponent implements OnInit {
  @Input() initiativeId!: string;
  private readonly api = inject(ApiService);
  dependencies = signal<any[]>([]);
  rollups = signal<any>({});
  initiatives = signal<any[]>([]);
  creating = signal(false);
  error = signal('');
  draft: any = {
    upstream_initiative_id: '',
    downstream_initiative_id: '',
    dependency_type: 'blocks',
    status: 'active',
    severity: 'medium',
    due_date: '',
    resolution_notes: '',
  };

  ngOnInit(): void {
    this.loadDependencies();
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe(res => {
      const items = res.items || [];
      this.initiatives.set(items);
      this.draft.upstream_initiative_id = items.find((item: any) => item.id !== this.initiativeId)?.id || '';
      this.draft.downstream_initiative_id = this.initiativeId;
    });
  }

  loadDependencies(): void {
    this.api.get<any>(`/initiatives/${this.initiativeId}/dependencies`).subscribe(res => {
      this.dependencies.set(res.items || []);
      this.rollups.set(res.rollups || {});
    });
  }

  createDependency(): void {
    this.error.set('');
    if (!this.draft.upstream_initiative_id || !this.draft.downstream_initiative_id) return;
    if (this.draft.upstream_initiative_id === this.draft.downstream_initiative_id) {
      this.error.set('Choose different upstream and downstream initiatives.');
      return;
    }
    this.creating.set(true);
    const body = { ...this.draft };
    if (!body.due_date) body.due_date = null;
    if (!body.resolution_notes) body.resolution_notes = null;
    this.api.post('/initiative-dependencies', body).subscribe({
      next: () => {
        this.creating.set(false);
        this.draft.resolution_notes = '';
        this.loadDependencies();
      },
      error: err => {
        this.creating.set(false);
        this.error.set(err?.error?.detail || 'Could not create dependency.');
      },
    });
  }

  statsCards() {
    const r = this.rollups();
    return [
      { label: 'Total', value: r.total || 0 },
      { label: 'Blocking', value: r.blocking || 0 },
      { label: 'At Risk', value: r.at_risk || 0 },
      { label: 'Overdue', value: r.overdue || 0 },
      { label: 'Critical Path', value: r.critical_path_risk || 0 },
    ];
  }
}
