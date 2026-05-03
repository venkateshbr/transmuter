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
            <option value="not_started">Not Started</option>
            <option value="in_progress">In Progress</option>
            <option value="overdue">Overdue</option>
            <option value="complete">Complete</option>
          </select>
          <input [(ngModel)]="searchQuery" (input)="applyFilters()" placeholder="Search..." class="input-field text-xs h-9 w-48" />
        </div>
      </div>

      <!-- Stats Summary -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-500">
            <span class="material-icons text-xl">event</span>
          </div>
          <div>
            <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-wider">Total</p>
            <p class="text-xl font-black text-[var(--t-text-primary)]">{{ stats()?.total || 0 }}</p>
          </div>
        </div>
        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center text-red-500">
            <span class="material-icons text-xl">warning</span>
          </div>
          <div>
            <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-wider">Overdue</p>
            <p class="text-xl font-black text-red-500">{{ stats()?.overdue || 0 }}</p>
          </div>
        </div>
        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
            <span class="material-icons text-xl">schedule</span>
          </div>
          <div>
            <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-wider">At Risk</p>
            <p class="text-xl font-black text-[var(--t-accent)]">{{ stats()?.at_risk || 0 }}</p>
          </div>
        </div>
        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center text-green-500">
            <span class="material-icons text-xl">check_circle</span>
          </div>
          <div>
            <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-wider">Complete</p>
            <p class="text-xl font-black text-green-500">{{ stats()?.complete || 0 }}</p>
          </div>
        </div>
      </div>

      <!-- Milestone Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        @for (m of filteredMilestones(); track m.id) {
          <div class="card p-6 flex flex-col hover:border-[var(--t-accent)] hover:shadow-xl transition-all group cursor-pointer"
               [routerLink]="['/initiatives', m.initiative_id]">
            
            <div class="flex justify-between items-start mb-4">
              <span class="badge" [class]="getStatusClass(m.status)">
                {{ m.status | uppercase }}
              </span>
              <div class="flex flex-col items-end">
                <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Due</span>
                <span class="text-xs font-mono font-bold" [class.text-red-500]="isDelayed(m)">
                  {{ m.planned_end | date:'MMM d, y' }}
                </span>
              </div>
            </div>

            <h3 class="text-lg font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors line-clamp-2 min-h-[3.5rem]">
              {{ m.name }}
            </h3>

            <div class="mt-4 flex items-center gap-2">
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--t-surface-raised)] text-[var(--t-accent)]">
                {{ m.initiative_code || 'GEN' }}
              </span>
              <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] truncate">
                {{ m.initiative_name }}
              </span>
            </div>

            <div class="mt-6 pt-6 border-t border-[var(--t-border)] flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex items-center justify-center text-[10px] font-bold">
                  {{ (m.owner_name || 'U').substring(0,1) }}
                </div>
                <span class="text-[10px] font-bold text-[var(--t-text-secondary)]">{{ m.owner_name || 'Unassigned' }}</span>
              </div>
              <div class="flex flex-col items-end gap-1">
                <div class="flex items-center gap-1">
                   <span class="text-[9px] font-black uppercase tracking-tighter text-[var(--t-text-tertiary)]">Pressure</span>
                   <span class="text-[10px] font-black" [style.color]="getPressureColor(m.pressure_score)">
                     {{ m.pressure_score || '0.0' }}
                   </span>
                </div>
                <div class="w-16 h-1 bg-[var(--t-border)] rounded-full overflow-hidden">
                   <div class="h-full transition-all duration-500"
                        [style.width.%]="(m.pressure_score || 0) * 10"
                        [style.background]="getPressureColor(m.pressure_score)"></div>
                </div>
              </div>
            </div>
          </div>
        }
        
        @if (filteredMilestones().length === 0) {
          <div class="col-span-full py-24 text-center border-2 border-dashed border-[var(--t-border)] rounded-3xl opacity-50">
             <span class="material-icons text-4xl mb-2 text-[var(--t-text-tertiary)]">event_busy</span>
             <p class="text-sm font-medium">No milestones found matching your criteria.</p>
          </div>
        }
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
  stats = signal<any>(null);
  
  searchQuery = '';
  statusFilter = '';

  ngOnInit() {
    this.api.get<any>('/portfolio/milestones').subscribe(res => {
      this.milestones.set(res.items || []);
      this.stats.set(res.stats || null);
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
      case 'overdue': return 'badge-red';
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

  isDelayed(m: any): boolean {
    if (m.status === 'complete') return false;
    return m.status === 'overdue' || new Date(m.planned_end) < new Date();
  }
}
