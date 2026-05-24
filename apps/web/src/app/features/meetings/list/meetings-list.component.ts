import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CompactFilterToolbarComponent, type CompactFilterGroup } from '../../../shared/components/compact-filter-toolbar/compact-filter-toolbar.component';

const MEETINGS_FILTER_STATE_KEY = 'transmuter.filters.meetings.list';

@Component({
  selector: 'app-meetings-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CompactFilterToolbarComponent],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      <div class="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Meetings<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Manage recurring workstream reviews and steering committees.</p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button (click)="showCreate.set(true)" class="btn-primary text-sm flex items-center gap-2" aria-label="Create meeting series">
          <span>+</span> New Series
        </button>
        </div>
      </div>

      <app-compact-filter-toolbar
        [searchValue]="search"
        searchPlaceholder="Search meetings"
        [groups]="meetingFilterGroups()"
        [hasFilters]="hasMeetingFilters()"
        (searchValueChange)="onSearchChange($event)"
        (groupSelectionChange)="onFilterGroupChange($event)"
        (clearFilters)="clearMeetingFilters()" />

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        @for (m of filteredMeetings(); track m.id) {
          <div class="card p-8 flex flex-col hover:border-[var(--t-accent)] hover:shadow-2xl transition-all cursor-pointer group relative overflow-hidden"
               [routerLink]="['/meetings', m.id]">
            
            <div class="absolute top-0 right-0 w-32 h-32 bg-[var(--t-accent-soft)]/20 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>

            <div class="flex justify-between items-start mb-6">
              <div class="flex flex-col">
                 <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)] mb-1">
                   {{ m.recurrence }}
                 </span>
                 <div class="flex items-center gap-1.5 text-[var(--t-text-tertiary)]">
                   <span class="material-icons text-xs">schedule</span>
                   <span class="text-[10px] font-bold">14:00 (GMT+8)</span>
                 </div>
              </div>
              <div class="flex -space-x-3">
                @for (i of [1,2,3]; track i) {
                  <div class="w-8 h-8 rounded-full border-2 border-[var(--t-surface)] bg-[var(--t-surface-raised)] flex items-center justify-center text-[10px] font-bold">
                    {{ i }}
                  </div>
                }
              </div>
            </div>

            <h3 class="text-xl font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors mb-3">
              {{ m.name }}
            </h3>
            
            <p class="text-sm text-[var(--t-text-secondary)] mb-8 line-clamp-2 leading-relaxed">
              {{ m.description || 'Enterprise-wide alignment session focused on strategic value delivery and cross-workstream dependencies.' }}
            </p>

            <div class="mt-auto pt-6 border-t border-[var(--t-border)] flex justify-between items-center">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-accent)]">
                   <span class="material-icons text-lg">person</span>
                </div>
                <div class="flex flex-col">
                   <span class="text-[10px] font-black text-[var(--t-text-primary)]">{{ m.users?.display_name }}</span>
                   <span class="text-[8px] font-bold uppercase text-[var(--t-text-tertiary)]">Lead</span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                 <span class="text-[9px] font-black uppercase tracking-tighter px-2 py-1 rounded bg-[var(--t-surface-raised)] border border-[var(--t-border)] text-[var(--t-text-secondary)]">
                   {{ m.workstreams?.name || 'All BU' }}
                 </span>
                 <span class="text-[9px] font-black uppercase tracking-tighter px-2 py-1 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                   {{ m.stats?.open_actions || 0 }} open
                 </span>
              </div>
            </div>
          </div>
        }
      </div>

      @if (filteredMeetings().length === 0) {
        <div class="flex flex-col items-center justify-center py-24 text-center">
          <div class="w-16 h-16 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center mb-4">
             <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[var(--t-text-tertiary)]"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
          <h3 class="text-lg font-bold text-[var(--t-text-primary)]">No meetings scheduled</h3>
          <p class="text-sm text-[var(--t-text-secondary)] mt-1 max-w-xs mx-auto">
            You haven't created any meeting series yet. Start by creating a weekly review or steering committee.
          </p>
        </div>
      }

      @if (showCreate()) {
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
          <form (ngSubmit)="createMeeting()" class="card w-full max-w-xl p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-bold text-[var(--t-text-primary)]">New meeting series</h2>
                <p class="text-sm text-[var(--t-text-secondary)] mt-1">Create a recurring forum backed by real sample-data APIs.</p>
              </div>
              <button type="button" (click)="showCreate.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close new meeting dialog">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label class="md:col-span-2">
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Name</span>
                <input [(ngModel)]="draft.name" name="name" required class="input-field w-full" aria-label="Meeting name" />
              </label>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Scope</span>
                <select [(ngModel)]="draft.scope" name="scope" class="input-field w-full" aria-label="Meeting scope">
                  <option value="all">All</option>
                  <option value="workstream">Workstream</option>
                  <option value="initiative">Initiative</option>
                </select>
              </label>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Recurrence</span>
                <select [(ngModel)]="draft.recurrence" name="recurrence" class="input-field w-full" aria-label="Meeting recurrence">
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Biweekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>
              <label class="md:col-span-2">
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Owner</span>
                <select [(ngModel)]="draft.owner_id" name="owner_id" required class="input-field w-full" aria-label="Meeting owner">
                  @for (u of users(); track u.id) {
                    <option [value]="u.id">{{ u.display_name || u.email }}</option>
                  }
                </select>
              </label>
              <label class="md:col-span-2">
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Description</span>
                <textarea [(ngModel)]="draft.description" name="description" rows="3" class="input-field w-full resize-none" aria-label="Meeting description"></textarea>
              </label>
            </div>

            @if (error()) {
              <p class="text-sm text-red-500">{{ error() }}</p>
            }

            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="showCreate.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" [disabled]="saving()" class="btn-primary text-sm">{{ saving() ? 'Creating...' : 'Create series' }}</button>
            </div>
          </form>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class MeetingsListComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  meetings = signal<any[]>([]);
  users = signal<any[]>([]);
  search = '';
  scopeFilter = '';
  showCreate = signal(false);
  saving = signal(false);
  error = signal<string | null>(null);
  draft = this.emptyDraft();

  filteredMeetings() {
    const term = this.search.trim().toLowerCase();
    return this.meetings().filter(m => {
      const matchesTerm = !term
        || `${m.name || ''} ${m.description || ''}`.toLowerCase().includes(term);
      const matchesScope = !this.scopeFilter || m.scope === this.scopeFilter;
      return matchesTerm && matchesScope;
    });
  }

  ngOnInit() {
    this.restoreMeetingFilters();
    this.loadMeetings();
    this.api.get<any>('/users').subscribe(res => {
      const users = res.data || [];
      this.users.set(users);
      if (!this.draft.owner_id && users.length) {
        this.draft.owner_id = users[0].id;
      }
    });
  }

  loadMeetings() {
    this.persistMeetingFilters();
    this.api.get<any>('/meetings').subscribe(res => {
      this.meetings.set(res.items || []);
    });
  }

  meetingFilterGroups(): CompactFilterGroup[] {
    return [
      {
        key: 'scope',
        label: 'Scope',
        mode: 'single',
        selected: this.scopeFilter ? [this.scopeFilter] : [],
        options: [
          { id: 'all', name: 'All' },
          { id: 'workstream', name: 'Workstream' },
          { id: 'initiative', name: 'Initiative' },
        ],
      },
    ];
  }

  onSearchChange(value: string): void {
    this.search = value;
    this.persistMeetingFilters();
  }

  onFilterGroupChange(change: { key: string; selected: string[] }): void {
    if (change.key === 'scope') this.scopeFilter = change.selected[0] || '';
    this.persistMeetingFilters();
  }

  clearMeetingFilters(): void {
    this.search = '';
    this.scopeFilter = '';
    this.persistMeetingFilters();
  }

  hasMeetingFilters(): boolean {
    return Boolean(this.search.trim() || this.scopeFilter);
  }

  private persistMeetingFilters(): void {
    localStorage.setItem(MEETINGS_FILTER_STATE_KEY, JSON.stringify({
      search: this.search,
      scopeFilter: this.scopeFilter,
    }));
  }

  private restoreMeetingFilters(): void {
    try {
      const raw = localStorage.getItem(MEETINGS_FILTER_STATE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw) as Record<string, string>;
      this.search = typeof state['search'] === 'string' ? state['search'] : '';
      this.scopeFilter = typeof state['scopeFilter'] === 'string' ? state['scopeFilter'] : '';
    } catch {
      localStorage.removeItem(MEETINGS_FILTER_STATE_KEY);
    }
  }

  createMeeting() {
    if (!this.draft.owner_id && this.users().length) {
      this.draft.owner_id = this.users()[0].id;
    }
    if (!this.draft.name.trim() || !this.draft.owner_id) {
      this.error.set('Name and owner are required.');
      return;
    }

    this.saving.set(true);
    this.error.set(null);
    this.api.post<any>('/meetings', {
      ...this.draft,
      name: this.draft.name.trim(),
      description: this.draft.description?.trim() || null,
    }).subscribe({
      next: meeting => {
        this.saving.set(false);
        this.showCreate.set(false);
        this.draft = this.emptyDraft();
        this.router.navigate(['/meetings', meeting.id]);
      },
      error: err => {
        this.saving.set(false);
        this.error.set(err.error?.detail || 'Could not create meeting.');
      },
    });
  }

  private emptyDraft() {
    return {
      name: '',
      scope: 'all',
      recurrence: 'weekly',
      description: '',
      owner_id: '',
    };
  }
}
