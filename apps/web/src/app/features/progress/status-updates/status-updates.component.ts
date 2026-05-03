import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface ComplianceInitiative {
  initiative_id: string;
  initiative_name: string;
  owner_name: string;
  last_update_at: string | null;
  days_since: number;
  status: 'on_time' | 'overdue' | 'nuclear';
  rag_status: 'green' | 'amber' | 'red';
  nudge_count: number;
}

interface StatusUpdate {
  id: string;
  initiative_name: string;
  author_name: string;
  rag_status: 'green' | 'amber' | 'red';
  summary: string;
  submitted_at: string;
}

type ComplianceFilter = 'all' | 'nuclear' | 'overdue' | 'on_time';

@Component({
  selector: 'app-status-updates',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Status Updates<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Portfolio reporting health and recent activity.</p>
        </div>
        <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <a routerLink="/progress" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Milestones</a>
             <a routerLink="/progress/roadmap" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Roadmap</a>
             <a routerLink="/progress/action-items" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Action Items</a>
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Status Updates</button>
             <a routerLink="/progress/dependencies" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Dependencies</a>
        </div>
      </div>

      @if (feedback()) {
        <div class="rounded-lg border px-4 py-3 text-sm font-medium"
             style="border-color:var(--t-border);background:var(--t-accent-soft);color:var(--t-accent)">
          {{ feedback() }}
        </div>
      }

      <!-- Stats Bar -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8" data-testid="status-compliance-summary">
        <div class="card p-6 bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm">
          <p class="text-sm font-medium text-[var(--t-text-secondary)]">Total Initiatives</p>
          <p class="text-3xl font-bold mt-1">{{ stats()?.summary?.total || 0 }}</p>
        </div>
        <div class="card p-6 bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm">
          <p class="text-sm font-medium text-[var(--t-text-secondary)]">On Time</p>
          <div class="flex items-center gap-2 mt-1">
            <p class="text-3xl font-bold text-emerald-500">{{ stats()?.summary?.on_time || 0 }}</p>
            <span class="badge-emerald px-2 py-0.5 rounded text-xs font-semibold">WEEKLY</span>
          </div>
        </div>
        <div class="card p-6 bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm">
          <p class="text-sm font-medium text-[var(--t-text-secondary)]">Overdue</p>
          <p class="text-3xl font-bold mt-1 text-amber-500">{{ stats()?.summary?.overdue || 0 }}</p>
        </div>
        <div class="card p-6 bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm">
          <p class="text-sm font-medium text-[var(--t-text-secondary)]">Nuclear</p>
          <p class="text-3xl font-bold mt-1 text-red-500">{{ stats()?.summary?.nuclear || 0 }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-[var(--t-border)] mb-6 gap-8">
        <button 
          (click)="activeTab.set('compliance')"
          [class.border-[var(--t-accent)]]="activeTab() === 'compliance'"
          [class.text-[var(--t-accent)]]="activeTab() === 'compliance'"
          class="pb-4 px-1 font-medium transition-colors border-b-2 border-transparent hover:text-[var(--t-accent)]">
          Compliance
        </button>
        <button 
          (click)="activeTab.set('recent')"
          [class.border-[var(--t-accent)]]="activeTab() === 'recent'"
          [class.text-[var(--t-accent)]]="activeTab() === 'recent'"
          class="pb-4 px-1 font-medium transition-colors border-b-2 border-transparent hover:text-[var(--t-accent)]">
          Recent Updates
        </button>
        <button 
          (click)="activeTab.set('nudges')"
          [class.border-[var(--t-accent)]]="activeTab() === 'nudges'"
          [class.text-[var(--t-accent)]]="activeTab() === 'nudges'"
          class="pb-4 px-1 font-medium transition-colors border-b-2 border-transparent hover:text-[var(--t-accent)]">
          Nudge Log
        </button>
      </div>

      <!-- Compliance Tab -->
      @if (activeTab() === 'compliance') {
        <div class="flex flex-wrap items-center gap-2" data-testid="status-compliance-filters">
          @for (filter of complianceFilters; track filter.value) {
            <button
              type="button"
              (click)="complianceFilter.set(filter.value)"
              [attr.aria-pressed]="complianceFilter() === filter.value"
              class="h-9 rounded-lg border px-4 text-xs font-bold uppercase tracking-wide transition-all"
              [style.border-color]="complianceFilter() === filter.value ? 'var(--t-accent)' : 'var(--t-border)'"
              [style.background]="complianceFilter() === filter.value ? 'var(--t-accent-soft)' : 'var(--t-surface)'"
              [style.color]="complianceFilter() === filter.value ? 'var(--t-accent)' : 'var(--t-text-secondary)'">
              {{ filter.label }}
              <span class="ml-2 font-black">{{ filter.count() }}</span>
            </button>
          }
        </div>

        <div class="card overflow-hidden bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm" data-testid="status-compliance-list">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-[var(--t-surface)] border-b border-[var(--t-border)]">
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">STATUS</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">INITIATIVE</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">OWNER</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)] text-center">LAST UPDATE</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)] text-center">DAYS SINCE</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)] text-center">NUDGES</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)] text-right">ACTION</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (item of filteredCompliance(); track item.initiative_id) {
                <tr class="hover:bg-[var(--t-surface)] transition-colors group">
                  <td class="px-6 py-4">
                    <span [class]="getStatusClass(item.status)" class="px-2 py-1 rounded text-xs font-bold uppercase tracking-wider">
                      {{ item.status.replace('_', ' ') }}
                    </span>
                  </td>
                  <td class="px-6 py-4 font-medium">{{ item.initiative_name }}</td>
                  <td class="px-6 py-4 text-[var(--t-text-secondary)]">{{ item.owner_name || 'Unassigned' }}</td>
                  <td class="px-6 py-4 text-center">
                    <div class="flex flex-col items-center">
                      <span class="text-sm font-medium">{{ item.last_update_at ? (item.last_update_at | date:'mediumDate') : 'Never' }}</span>
                      @if (item.days_since < 999) {
                        <span class="text-xs text-[var(--t-text-secondary)]">{{ item.days_since }} days ago</span>
                      }
                    </div>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span class="text-sm font-bold">{{ item.days_since >= 999 ? 'Never' : item.days_since }}</span>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span class="inline-flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-xs font-bold"
                          style="background:var(--t-surface-raised);color:var(--t-text-secondary);border:1px solid var(--t-border)">
                      {{ item.nudge_count || 0 }}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-right">
                    <button 
                      type="button"
                      (click)="nudge(item.initiative_id)"
                      [disabled]="item.status === 'on_time'"
                      [class.opacity-50]="item.status === 'on_time'"
                      [class.cursor-not-allowed]="item.status === 'on_time'"
                      aria-label="Send status update nudge"
                      title="Send status update nudge"
                      class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--t-accent)] transition-all hover:bg-[var(--t-accent-soft)] disabled:opacity-50">
                      <span class="material-icons text-lg">notifications_active</span>
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="px-6 py-12 text-center text-[var(--t-text-secondary)]">No initiatives match this compliance filter.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      <!-- Recent Updates Tab -->
      @if (activeTab() === 'recent') {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          @for (update of recentUpdates(); track update.id) {
            <div class="card p-6 bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm hover:shadow-md transition-all">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h3 class="font-bold text-lg">{{ update.initiative_name }}</h3>
                  <p class="text-xs text-[var(--t-text-secondary)] mt-1">Submitted by {{ update.author_name }} • {{ update.submitted_at | date:'medium' }}</p>
                </div>
                <span [class]="getRagClass(update.rag_status)" class="px-3 py-1 rounded-full text-xs font-black uppercase shadow-sm">
                  {{ update.rag_status }}
                </span>
              </div>
              <p class="text-sm text-[var(--t-text-secondary)] line-clamp-3 leading-relaxed">
                {{ update.summary }}
              </p>
              <button class="mt-4 text-[var(--t-accent)] text-sm font-semibold hover:underline flex items-center gap-1">
                Read full update 
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          } @empty {
            <div class="col-span-2 text-center py-20 bg-[var(--t-surface)] rounded-lg border border-dashed border-[var(--t-border)]">
              <p class="text-[var(--t-text-secondary)]">No status updates have been submitted yet.</p>
            </div>
          }
        </div>
      }

      <!-- Nudge Log Tab -->
      @if (activeTab() === 'nudges') {
        <div class="card overflow-hidden bg-white dark:bg-[#1e1b2e] border border-[var(--t-border)] rounded-lg shadow-sm" data-testid="status-nudge-log">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-[var(--t-surface)] border-b border-[var(--t-border)]">
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">SENT AT</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">INITIATIVE</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)]">SENT BY</th>
                <th class="px-6 py-4 text-sm font-semibold text-[var(--t-text-secondary)] text-right">CHANNEL</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (nudge of nudges(); track nudge.id) {
                <tr class="hover:bg-[var(--t-surface)] transition-colors">
                  <td class="px-6 py-4 text-sm">{{ nudge.sent_at | date:'medium' }}</td>
                  <td class="px-6 py-4 font-medium">{{ nudge.initiatives?.name }}</td>
                  <td class="px-6 py-4 text-[var(--t-text-secondary)]">{{ nudge.users?.display_name || 'System' }}</td>
                  <td class="px-6 py-4 text-right">
                    <span class="badge-purple px-2 py-1 rounded text-[10px] font-bold uppercase">{{ nudge.channel }}</span>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4" class="px-6 py-12 text-center text-[var(--t-text-secondary)]">No nudges have been sent yet.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class StatusUpdatesComponent implements OnInit {
  private api = inject(ApiService);
  
  activeTab = signal<'compliance' | 'recent' | 'nudges'>('compliance');
  complianceFilter = signal<ComplianceFilter>('all');
  stats = signal<any>(null);
  recentUpdates = signal<StatusUpdate[]>([]);
  nudges = signal<any[]>([]);
  feedback = signal<string | null>(null);
  filteredCompliance = computed(() => {
    const rows = (this.stats()?.initiatives || []) as ComplianceInitiative[];
    const filter = this.complianceFilter();
    return filter === 'all' ? rows : rows.filter(row => row.status === filter);
  });
  complianceFilters = [
    { label: 'All', value: 'all' as ComplianceFilter, count: () => this.stats()?.summary?.total || 0 },
    { label: 'Nuclear', value: 'nuclear' as ComplianceFilter, count: () => this.stats()?.summary?.nuclear || 0 },
    { label: 'Overdue', value: 'overdue' as ComplianceFilter, count: () => this.stats()?.summary?.overdue || 0 },
    { label: 'On Time', value: 'on_time' as ComplianceFilter, count: () => this.stats()?.summary?.on_time || 0 },
  ];

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.get<any>('/status-updates/compliance').subscribe(data => {
      this.stats.set(data);
    });
    this.api.get<StatusUpdate[]>('/status-updates/portfolio').subscribe(data => {
      this.recentUpdates.set(data);
    });
    this.api.get<any[]>('/status-updates/nudges').subscribe(data => {
      this.nudges.set(data);
    });
  }

  nudge(initiativeId: string) {
    this.api.post<any>(`/initiatives/${initiativeId}/nudge`, { channel: 'both' }).subscribe(() => {
      this.feedback.set('Nudge queued for the initiative owner.');
      this.loadData();
      setTimeout(() => this.feedback.set(null), 3500);
    });
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'on_time': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'overdue': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
      case 'nuclear': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  }

  getRagClass(rag: string): string {
    switch (rag) {
      case 'green': return 'bg-emerald-500 text-white';
      case 'amber': return 'bg-amber-500 text-white';
      case 'red': return 'bg-red-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  }
}
