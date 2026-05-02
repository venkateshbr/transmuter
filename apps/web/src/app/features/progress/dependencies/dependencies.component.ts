import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dependencies',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Cross-Initiative Dependencies<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Visualize and manage links between milestones across the portfolio.</p>
        </div>
        <div class="flex gap-3 items-center">
          <div class="flex bg-[var(--t-surface-raised)] rounded-lg p-1 border border-[var(--t-border)] h-9 items-center">
             <a routerLink="/progress" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Milestones</a>
             <a routerLink="/progress/roadmap" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Roadmap</a>
             <a routerLink="/progress/action-items" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Action Items</a>
             <button class="px-4 py-1 text-xs font-medium rounded-md bg-[var(--t-surface)] text-[var(--t-accent)] shadow-sm">Dependencies</button>
          </div>
          <button class="btn-primary text-sm h-9 flex items-center gap-2">
            <span>+</span> Link Milestones
          </button>
        </div>
      </div>

      <!-- Dependency Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        @for (d of dependencies(); track d.id) {
          <div class="card p-6 border-l-4 border-[var(--t-accent)] hover:shadow-lg transition-all group">
            <div class="flex items-center justify-between gap-4">
              
              <!-- Upstream (Pre-requisite) -->
              <div class="flex-1">
                <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-2">Upstream</p>
                <h4 class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                  {{ d.upstream?.name }}
                </h4>
                <p class="text-[10px] text-[var(--t-accent)] font-bold mt-1">
                  {{ d.upstream?.initiative_code }}
                </p>
              </div>

              <!-- Connection -->
              <div class="flex flex-col items-center">
                 <div class="w-12 h-px bg-[var(--t-border)] relative">
                    <div class="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 border-t-2 border-r-2 border-[var(--t-border)] rotate-45"></div>
                 </div>
                 <span class="text-[8px] font-bold text-[var(--t-text-tertiary)] uppercase mt-2">Blocks</span>
              </div>

              <!-- Downstream (Dependent) -->
              <div class="flex-1 text-right">
                <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-2">Downstream</p>
                <h4 class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                  {{ d.downstream?.name }}
                </h4>
                <p class="text-[10px] text-[var(--t-accent)] font-bold mt-1">
                  {{ d.downstream?.initiative_code }}
                </p>
              </div>

            </div>
          </div>
        }
        @if (dependencies().length === 0) {
          <div class="col-span-2 py-24 text-center">
            <p class="text-xs text-[var(--t-text-tertiary)]">No cross-milestone dependencies identified.</p>
          </div>
        }
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

  ngOnInit() {
    this.api.get<any>('/dependencies').subscribe(res => {
      this.dependencies.set(res.items || []);
    });
  }
}
