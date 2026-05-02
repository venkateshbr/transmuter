import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-milestones',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Milestone Tracker<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Portfolio-wide milestone status and deadline tracking.</p>
        </div>
        <div class="flex gap-3 items-center">
          <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Milestones</button>
             <a routerLink="/progress/roadmap" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Roadmap</a>
             <a routerLink="/progress/action-items" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Action Items</a>
             <a routerLink="/progress/dependencies" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Dependencies</a>
          </div>
          <select [(ngModel)]="statusFilter" (change)="applyFilters()" class="input-field text-xs h-9 w-32">
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="delayed">Delayed</option>
            <option value="complete">Complete</option>
          </select>
          <input [(ngModel)]="searchQuery" (input)="applyFilters()" placeholder="Search milestones..." class="input-field text-xs h-9 w-48" />
        </div>
      </div>

      <!-- Milestone Table -->
      <div class="card overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-[var(--t-surface-raised)] border-b border-[var(--t-border)]">
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Milestone</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] text-center">Pressure</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Owner</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Planned End</th>
              <th class="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--t-border)]">
            @for (m of filteredMilestones(); track m.id) {
              <tr class="hover:bg-[var(--t-surface-raised)] transition-colors group">
                <td class="px-6 py-4">
                  <div class="flex flex-col">
                    <span class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                      {{ m.name }}
                    </span>
                    <span class="text-[10px] text-[var(--t-text-tertiary)] mt-0.5">ID: {{ m.id.substring(0, 8) }}</span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="badge" [class]="getStatusClass(m.status)">
                    {{ m.status | uppercase }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-col items-center gap-1">
                    <span class="text-xs font-mono font-bold" [style.color]="getPressureColor(m.pressure_score)">
                      {{ m.pressure_score || '0.0' }}
                    </span>
                    <div class="w-12 h-1 bg-[var(--t-border)] rounded-full overflow-hidden">
                       <div class="h-full transition-all duration-500"
                            [style.width.%]="(m.pressure_score || 0) * 10"
                            [style.background]="getPressureColor(m.pressure_score)"></div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] flex items-center justify-center text-[10px] text-white font-bold">
                      {{ (m.owner_name || 'U').substring(0,1) }}
                    </div>
                    <span class="text-xs text-[var(--t-text-secondary)]">{{ m.owner_name || 'Unassigned' }}</span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs font-mono text-[var(--t-text-secondary)]">
                    {{ m.planned_end | date:'MMM d, y' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button class="text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
                  </button>
                </td>
              </tr>
            }
            @if (filteredMilestones().length === 0) {
              <tr>
                <td colspan="6" class="px-6 py-12 text-center text-xs text-[var(--t-text-tertiary)]">
                  No milestones found matching your criteria.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class MilestonesComponent implements OnInit {
  private readonly api = inject(ApiService);
  
  milestones = signal<any[]>([]);
  filteredMilestones = signal<any[]>([]);
  
  searchQuery = '';
  statusFilter = '';

  ngOnInit() {
    this.api.get<any>('/milestones').subscribe(res => {
      this.milestones.set(res.items || []);
      this.applyFilters();
    });
  }

  applyFilters() {
    let filtered = [...this.milestones()];
    
    if (this.statusFilter) {
      filtered = filtered.filter(m => m.status === this.statusFilter);
    }
    
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      filtered = filtered.filter(m => 
        m.name.toLowerCase().includes(q) || 
        (m.owner_name || '').toLowerCase().includes(q)
      );
    }
    
    this.filteredMilestones.set(filtered);
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'complete': return 'badge-green';
      case 'delayed': return 'badge-red';
      case 'in_progress': return 'badge-purple';
      default: return '';
    }
  }

  getPressureColor(score: string | number): string {
    const s = Number(score) || 0;
    if (s < 3.4) return 'var(--t-green)';
    if (s < 6.7) return 'var(--t-amber)';
    return 'var(--t-red)';
  }
}
