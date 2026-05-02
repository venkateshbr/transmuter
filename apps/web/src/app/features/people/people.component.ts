import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-people',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            People<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Manage team roles, workload, and performance tracking.</p>
        </div>
        <button class="btn-primary text-sm flex items-center gap-2">
          <span>+</span> Invite User
        </button>
      </div>

      <!-- People Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        @for (p of people(); track p.id) {
          <div class="card p-6 flex flex-col items-center text-center hover:border-[var(--t-accent)] transition-all cursor-pointer group">
            <div class="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] flex items-center justify-center text-xl text-white font-bold mb-4 shadow-lg group-hover:scale-110 transition-transform">
              {{ (p.display_name || 'U').substring(0,1) }}
            </div>
            
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
              {{ p.display_name || 'Anonymous' }}
            </h3>
            <p class="text-xs text-[var(--t-text-tertiary)] font-bold uppercase tracking-widest mt-1">
              {{ p.role.replace('_', ' ') }}
            </p>
            <p class="text-xs text-[var(--t-text-secondary)] mt-2">{{ p.title || 'N/A' }}</p>

            <div class="w-full mt-6 pt-6 border-t border-[var(--t-border)] grid grid-cols-2 gap-4">
              <div>
                <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Initiatives</p>
                <p class="text-lg font-black text-[var(--t-text-primary)]">{{ p.initiative_count }}</p>
              </div>
              <div>
                <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Pressure</p>
                <p class="text-lg font-black" [style.color]="getPressureColor(p.pressure_score)">
                  {{ p.pressure_score.toFixed(1) }}
                </p>
              </div>
            </div>

            <div class="w-full mt-4 flex gap-2">
              <button class="flex-1 btn-ghost text-[10px] py-2">Profile</button>
              <button class="flex-1 btn-ghost text-[10px] py-2 text-red-500 hover:bg-red-500/10">Manage</button>
            </div>
          </div>
        }
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class PeopleComponent implements OnInit {
  private readonly api = inject(ApiService);
  people = signal<any[]>([]);

  ngOnInit() {
    this.api.get<any>('/people').subscribe(res => {
      this.people.set(res.items || []);
    });
  }

  getPressureColor(score: number): string {
    if (score < 3.4) return 'var(--t-green)';
    if (score < 6.7) return 'var(--t-amber)';
    return 'var(--t-red)';
  }
}
