import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

interface RoadmapMilestone {
  id: string;
  name: string;
  initiative_name: string;
  planned_end: string;
  status: string;
  pressure_score: string;
}

interface InitiativeGroup {
  name: string;
  milestones: RoadmapMilestone[];
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
             <a routerLink="/progress/dependencies" class="px-4 py-1 text-xs font-medium rounded-md text-[var(--t-text-tertiary)] hover:text-[var(--t-text-primary)] transition-colors">Dependencies</a>
          </div>
          <select [(ngModel)]="timeframe" class="input-field text-xs h-9 w-32">
            <option [value]="6">6 Months</option>
            <option [value]="12">12 Months</option>
            <option [value]="24">24 Months</option>
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
          <div class="space-y-6">
            @for (group of groupedMilestones(); track group.name) {
              <div class="grid grid-cols-[250px_1fr] group">
                <!-- Initiative Label -->
                <div class="pr-4 py-2">
                  <h3 class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors truncate" [title]="group.name">
                    {{ group.name }}
                  </h3>
                  <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ group.milestones.length }} milestones</p>
                </div>

                <!-- Milestone Lane -->
                <div class="relative h-12 flex items-center">
                  <!-- Grid Background Lines -->
                  <div class="absolute inset-0 flex pointer-events-none">
                    @for (month of months(); track month.label) {
                      <div class="flex-1 border-l border-[var(--t-border)]/30 h-full"></div>
                    }
                  </div>

                  <!-- Milestones -->
                  @for (m of group.milestones; track m.id) {
                    @if (getMilestonePosition(m.planned_end); as pos) {
                      <div class="absolute group/ms" 
                           [style.left.%]="pos"
                           [title]="m.name + ' (' + (m.planned_end | date:'mediumDate') + ')'">
                        <!-- Dot -->
                        <div class="w-3 h-3 rounded-full border-2 border-[var(--t-surface)] shadow-sm transition-transform group-hover/ms:scale-125 cursor-pointer"
                             [class]="getMilestoneStatusClass(m.status)"
                             [style.background]="getPressureColor(m.pressure_score)"></div>
                        
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
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-green)]"></span> Low Pressure</span>
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-amber)]"></span> Medium Pressure</span>
        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--t-red)]"></span> High Pressure</span>
        <span class="ml-auto">Markers indicate planned completion dates</span>
      </div>

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
  
  milestones = signal<RoadmapMilestone[]>([]);
  timeframe = 12; // months

  months = computed(() => {
    const months = [];
    const now = new Date();
    // Start from 1 month ago to show context
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    
    for (let i = 0; i < this.timeframe; i++) {
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
        new Date(a.planned_end).getTime() - new Date(b.planned_end).getTime()
      )
    }));
  });

  ngOnInit() {
    this.api.get<any>('/milestones').subscribe(res => {
      this.milestones.set(res.items || []);
    });
  }

  getMilestonePosition(dateStr: string): number {
    const date = new Date(dateStr);
    const start = this.months()[0].date;
    const end = new Date(this.months()[this.months().length - 1].date);
    end.setMonth(end.getMonth() + 1);

    const totalMs = end.getTime() - start.getTime();
    const currentMs = date.getTime() - start.getTime();
    
    return Math.max(0, Math.min(100, (currentMs / totalMs) * 100));
  }

  getMilestoneStatusClass(status: string): string {
    switch (status) {
      case 'complete': return 'opacity-60 grayscale-[0.5]';
      case 'delayed': return 'ring-2 ring-[var(--t-red)] ring-offset-2 ring-offset-[var(--t-surface)]';
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
