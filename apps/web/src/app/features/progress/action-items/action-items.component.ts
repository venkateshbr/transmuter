import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CompactFilterToolbarComponent, type CompactFilterGroup } from '../../../shared/components/compact-filter-toolbar/compact-filter-toolbar.component';

const ACTION_ITEM_FILTER_STATE_KEY = 'transmuter.filters.progress.action-items';

@Component({
  selector: 'app-action-items',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CompactFilterToolbarComponent],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Action Items<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Track and manage tasks assigned during transformation meetings.</p>
        </div>
        <div class="flex gap-3 items-center">
          <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <a routerLink="/progress" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Milestones</a>
             <a routerLink="/progress/roadmap" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Roadmap</a>
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Action Items</button>
          </div>
        </div>
      </div>

      <app-compact-filter-toolbar
        [showSearch]="false"
        [groups]="actionItemFilterGroups()"
        [hasFilters]="hasActionItemFilters()"
        (groupSelectionChange)="onFilterGroupChange($event)"
        (clearFilters)="clearActionItemFilters()" />

      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4" data-testid="action-item-stats">
        @for (card of statsCards(); track card.label) {
          <button
            type="button"
            class="card p-4 text-left hover:border-[var(--t-accent)] transition-colors"
            (click)="setStatusFilter(card.filter)"
          >
            <p class="text-[10px] font-bold uppercase tracking-wider mb-2" style="color:var(--t-text-secondary)">{{ card.label }}</p>
            <p class="text-2xl font-black" [style.color]="card.color">{{ card.value }}</p>
          </button>
        }
      </div>

      <!-- Action Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        @for (item of filteredItems(); track item.id) {
          <div class="card p-6 flex flex-col hover:border-[var(--t-accent)] hover:shadow-xl transition-all group">
            
            <div class="flex justify-between items-start mb-4">
              <div class="flex items-center gap-3">
	                 <input type="checkbox" [checked]="item.status === 'completed'"
                          (change)="toggleComplete(item)"
                          aria-label="Toggle action item complete"
	                        class="w-5 h-5 rounded-full border-2 border-[var(--t-border)] text-[var(--t-accent)] focus:ring-[var(--t-accent)] cursor-pointer transition-all">
                 <span class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded bg-[var(--t-surface-raised)] text-[var(--t-text-tertiary)]">
                   {{ item.priority }}
                 </span>
                 <span class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded"
                       [ngClass]="statusClass(item.status)">
                   {{ item.status.replace('_', ' ') }}
                 </span>
              </div>
              <span class="text-[10px] font-mono font-bold" [class.text-red-500]="isOverdue(item)">
                @if (item.due_date) {
                  Due {{ item.due_date | date:'MMM d' }}
                } @else {
                  No due date
                }
              </span>
            </div>

            <h3 class="text-base font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors line-clamp-2 min-h-[3rem]">
              {{ item.description }}
            </h3>

            <div class="mt-4 flex items-center gap-2">
               <span class="material-icons text-sm text-[var(--t-accent)]">rocket_launch</span>
               <span class="text-[10px] font-bold text-[var(--t-text-secondary)] truncate">
                 {{ item.initiatives?.name || 'General Platform' }}
               </span>
            </div>

            @if (item.meeting_sessions?.meeting_id) {
              <a
                [routerLink]="['/meetings', item.meeting_sessions.meeting_id]"
                class="mt-3 flex items-center gap-2 text-[10px] font-bold text-[var(--t-text-secondary)] hover:text-[var(--t-accent)] transition-colors"
              >
                <span class="material-icons text-sm">forum</span>
                <span class="truncate">{{ item.meeting_sessions?.meetings?.name || 'Meeting session' }}</span>
                <span>{{ item.meeting_sessions?.session_date | date:'MMM d' }}</span>
              </a>
            }

            <div class="mt-4 grid grid-cols-2 gap-2">
              <select
                class="input-field text-[11px] h-9"
                [ngModel]="item.status"
                (ngModelChange)="updateItem(item.id, { status: $event })"
                aria-label="Action item status"
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <input
                type="date"
                class="input-field text-[11px] h-9"
                [ngModel]="item.due_date"
                (change)="updateItem(item.id, { due_date: $any($event.target).value })"
                aria-label="Action item due date"
              />
            </div>

            <div class="mt-6 pt-6 border-t border-[var(--t-border)] flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--t-accent)] to-[var(--t-blue-light)] flex items-center justify-center text-[10px] text-white font-black shadow-sm">
                  {{ (item.users?.display_name || 'U').substring(0,1) }}
                </div>
                <div class="flex flex-col">
                  <span class="text-[10px] font-black text-[var(--t-text-primary)]">{{ item.users?.display_name || 'Unassigned' }}</span>
                  <span class="text-[8px] font-bold uppercase text-[var(--t-text-tertiary)]">Owner</span>
                </div>
              </div>
              
              <div class="flex gap-1">
	                <button (click)="cycleStatus(item)" class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] hover:bg-[var(--t-accent-soft)] transition-all" aria-label="Cycle action item status">
	                  <span class="material-icons text-sm">edit</span>
	                </button>
	                <button (click)="deleteItem(item.id)" class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-red-500 hover:bg-red-500/10 transition-all" aria-label="Delete action item">
	                  <span class="material-icons text-sm">delete_outline</span>
	                </button>
              </div>
            </div>
          </div>
        }
        
        @if (filteredItems().length === 0) {
          <div class="col-span-full py-24 text-center border-2 border-dashed border-[var(--t-border)] rounded-3xl opacity-50">
             <span class="material-icons text-4xl mb-2 text-[var(--t-text-tertiary)]">assignment_turned_in</span>
             <p class="text-sm font-medium">No action items found matching your criteria.</p>
          </div>
        }
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class ActionItemsComponent implements OnInit {
  private readonly api = inject(ApiService);
  
  items = signal<any[]>([]);
  filteredItems = signal<any[]>([]);
  stats = signal<any>({ total: 0, open: 0, in_progress: 0, completed: 0, cancelled: 0, overdue: 0 });
  statusFilter = '';

  ngOnInit() {
    this.restoreActionItemFilters();
    this.fetchItems();
  }

  fetchItems() {
    this.api.get<any>('/portfolio/action-items').subscribe(res => {
      this.items.set(res.items || []);
      this.stats.set(res.stats || { total: 0, open: 0, in_progress: 0, completed: 0, cancelled: 0, overdue: 0 });
      this.applyFilters();
    });
  }

  applyFilters() {
    this.persistActionItemFilters();
    let filtered = [...this.items()];
    if (this.statusFilter === 'overdue') {
      filtered = filtered.filter(i => this.isOverdue(i));
    } else if (this.statusFilter) {
      filtered = filtered.filter(i => i.status === this.statusFilter);
    }
    this.filteredItems.set(filtered);
  }

  setStatusFilter(filter: string) {
    this.statusFilter = filter;
    this.applyFilters();
  }

  actionItemFilterGroups(): CompactFilterGroup[] {
    return [
      {
        key: 'status',
        label: 'Status',
        mode: 'single',
        selected: this.statusFilter ? [this.statusFilter] : [],
        options: [
          { id: 'open', name: 'Open' },
          { id: 'in_progress', name: 'In Progress' },
          { id: 'completed', name: 'Completed' },
          { id: 'cancelled', name: 'Cancelled' },
          { id: 'overdue', name: 'Overdue' },
        ],
      },
    ];
  }

  onFilterGroupChange(change: { key: string; selected: string[] }): void {
    if (change.key === 'status') this.statusFilter = change.selected[0] || '';
    this.applyFilters();
  }

  clearActionItemFilters(): void {
    this.statusFilter = '';
    this.applyFilters();
  }

  hasActionItemFilters(): boolean {
    return Boolean(this.statusFilter);
  }

  private persistActionItemFilters(): void {
    localStorage.setItem(ACTION_ITEM_FILTER_STATE_KEY, JSON.stringify({
      statusFilter: this.statusFilter,
    }));
  }

  private restoreActionItemFilters(): void {
    try {
      const raw = localStorage.getItem(ACTION_ITEM_FILTER_STATE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw) as Record<string, string>;
      this.statusFilter = typeof state['statusFilter'] === 'string' ? state['statusFilter'] : '';
    } catch {
      localStorage.removeItem(ACTION_ITEM_FILTER_STATE_KEY);
    }
  }

  toggleComplete(item: any) {
    const status = item.status === 'completed' ? 'open' : 'completed';
    this.updateItem(item.id, { status });
  }

  cycleStatus(item: any) {
    const next = item.status === 'open'
      ? 'in_progress'
      : item.status === 'in_progress'
        ? 'completed'
        : item.status === 'completed'
          ? 'cancelled'
          : 'open';
    this.updateItem(item.id, { status: next });
  }

  deleteItem(id: string) {
    this.api.delete(`/action-items/${id}`).subscribe(() => {
      this.items.set(this.items().filter(item => item.id !== id));
      this.applyFilters();
    });
  }

  updateItem(id: string, body: Record<string, string>) {
    this.api.put<any>(`/action-items/${id}`, body).subscribe(updated => {
      this.items.set(this.items().map(item => item.id === id ? updated : item));
      this.fetchItems();
    });
  }

  statsCards() {
    const s = this.stats();
    return [
      { label: 'Total', value: s.total || 0, filter: '', color: 'var(--t-text-primary)' },
      { label: 'Open', value: s.open || 0, filter: 'open', color: 'var(--t-text-primary)' },
      { label: 'In Progress', value: s.in_progress || 0, filter: 'in_progress', color: 'var(--t-amber)' },
      { label: 'Completed', value: s.completed || 0, filter: 'completed', color: 'var(--t-green)' },
      { label: 'Cancelled', value: s.cancelled || 0, filter: 'cancelled', color: 'var(--t-red)' },
      { label: 'Overdue', value: s.overdue || 0, filter: 'overdue', color: 'var(--t-red)' },
    ];
  }

  statusClass(status: string): string {
    switch (status) {
      case 'completed': return 'bg-green-500 text-white';
      case 'in_progress': return 'bg-amber-500 text-white';
      case 'cancelled': return 'bg-red-500 text-white';
      default: return 'bg-[var(--t-surface-raised)] text-[var(--t-text-tertiary)]';
    }
  }

  getPriorityClass(p: string): string {
    switch (p) {
      case 'high': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'medium': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return '';
    }
  }

  isOverdue(item: any): boolean {
    if (item.status === 'completed' || item.status === 'cancelled' || !item.due_date) return false;
    return new Date(item.due_date) < new Date();
  }
}
