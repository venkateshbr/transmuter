import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-action-items',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
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
             <a routerLink="/progress/dependencies" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Dependencies</a>
          </div>
          <select [(ngModel)]="statusFilter" (change)="applyFilters()" class="input-field text-xs h-9 w-32">
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
          <button class="btn-primary text-sm h-9 flex items-center gap-2">
            <span>+</span> Log Action
          </button>
        </div>
      </div>

      <!-- Action Items List -->
      <div class="grid grid-cols-1 gap-4">
        @for (item of filteredItems(); track item.id) {
          <div class="card p-5 flex items-center gap-6 hover:border-[var(--t-accent)] transition-all group">
            <div class="flex-none">
              <input type="checkbox" [checked]="item.status === 'completed'" 
                     class="w-6 h-6 rounded-full border-2 border-[var(--t-border)] text-[var(--t-accent)] focus:ring-[var(--t-accent)] cursor-pointer">
            </div>
            
            <div class="flex-1">
              <h3 class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                {{ item.description }}
              </h3>
              <div class="flex items-center gap-4 mt-2">
                <span class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-accent)]">
                  {{ item.initiatives?.initiative_code || 'General' }}
                </span>
                <span class="text-[10px] text-[var(--t-text-tertiary)] flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                  Due {{ item.due_date | date:'MMM d' }}
                </span>
                <span class="text-[10px] text-[var(--t-text-tertiary)] flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  {{ item.users?.display_name || 'Unassigned' }}
                </span>
              </div>
            </div>

            <div class="flex-none flex items-center gap-3">
              <span class="badge" [class]="getPriorityClass(item.priority)">
                {{ item.priority | uppercase }}
              </span>
              <button class="text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)]">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
              </button>
            </div>
          </div>
        }
        @if (filteredItems().length === 0) {
          <div class="py-24 text-center">
            <p class="text-xs text-[var(--t-text-tertiary)]">No action items found.</p>
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
  statusFilter = 'open';

  ngOnInit() {
    this.fetchItems();
  }

  fetchItems() {
    this.api.get<any>('/action-items').subscribe(res => {
      this.items.set(res.items || []);
      this.applyFilters();
    });
  }

  applyFilters() {
    let filtered = [...this.items()];
    if (this.statusFilter) {
      filtered = filtered.filter(i => i.status === this.statusFilter);
    }
    this.filteredItems.set(filtered);
  }

  getPriorityClass(p: string): string {
    switch (p) {
      case 'high': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'medium': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return '';
    }
  }
}
