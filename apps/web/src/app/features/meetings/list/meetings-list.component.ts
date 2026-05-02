import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-meetings-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Meetings<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Manage recurring workstream reviews and steering committees.</p>
        </div>
        <button class="btn-primary text-sm flex items-center gap-2">
          <span>+</span> New Meeting Series
        </button>
      </div>

      <!-- Meeting Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        @for (m of meetings(); track m.id) {
          <div class="card p-6 flex flex-col hover:border-[var(--t-accent)] transition-all cursor-pointer group"
               [routerLink]="['/meetings', m.id]">
            <div class="flex justify-between items-start mb-4">
              <span class="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                {{ m.recurrence }}
              </span>
              <div class="flex -space-x-2">
                <div class="w-6 h-6 rounded-full border-2 border-[var(--t-surface)] bg-gray-400"></div>
                <div class="w-6 h-6 rounded-full border-2 border-[var(--t-surface)] bg-gray-500"></div>
                <div class="w-6 h-6 rounded-full border-2 border-[var(--t-surface)] bg-gray-600 flex items-center justify-center text-[8px] text-white">+3</div>
              </div>
            </div>

            <h3 class="text-lg font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors mb-2">
              {{ m.name }}
            </h3>
            <p class="text-sm text-[var(--t-text-secondary)] mb-6 line-clamp-2">
              {{ m.description || 'No description provided.' }}
            </p>

            <div class="mt-auto pt-4 border-t border-[var(--t-border)] flex justify-between items-center">
              <div class="flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[var(--t-text-tertiary)]"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span class="text-xs text-[var(--t-text-tertiary)]">{{ m.users?.display_name }}</span>
              </div>
              <span class="text-xs font-semibold text-[var(--t-text-secondary)]">
                {{ m.workstreams?.name || 'All' }}
              </span>
            </div>
          </div>
        }
      </div>

      @if (meetings().length === 0) {
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

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class MeetingsListComponent implements OnInit {
  private readonly api = inject(ApiService);
  meetings = signal<any[]>([]);

  ngOnInit() {
    this.api.get<any>('/meetings').subscribe(res => {
      this.meetings.set(res.items || []);
    });
  }
}
