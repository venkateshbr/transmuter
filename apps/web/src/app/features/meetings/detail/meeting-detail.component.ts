import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';

@Component({
  selector: 'app-meeting-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      @if (meeting(); as m) {
        <!-- Header -->
        <div class="flex justify-between items-start">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <a routerLink="/meetings" class="text-xs font-bold text-[var(--t-accent)] hover:underline uppercase tracking-widest">Meetings</a>
              <span class="text-[var(--t-text-tertiary)]">/</span>
              <span class="text-xs font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">{{ m.id.substring(0,8) }}</span>
            </div>
            <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
              {{ m.name }}<span class="text-[var(--t-accent)]">.</span>
            </h1>
            <p class="text-[var(--t-text-secondary)]">{{ m.description }}</p>
          </div>
          <div class="flex gap-2">
            <button class="btn-ghost text-sm">Edit Series</button>
            <button (click)="startSession()" class="btn-primary text-sm flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Start Session
            </button>
          </div>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Recurrence</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)] capitalize">{{ m.recurrence }}</p>
          </div>
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Scope</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)] capitalize">{{ m.scope }}</p>
          </div>
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Workstream</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ m.workstreams?.name || 'All' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Sessions</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ m.sessions?.length || 0 }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- Left: Agenda & Sessions -->
          <div class="lg:col-span-2 space-y-8">
            
            <!-- Agenda -->
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Next Agenda</h3>
                <button class="text-xs text-[var(--t-accent)] font-semibold">+ Add Item</button>
              </div>
              <div class="space-y-3">
                @for (item of m.agenda; track item.id) {
                  <div class="flex items-center gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-colors group">
                    <div class="w-6 h-6 rounded bg-[var(--t-bg-page)] flex items-center justify-center text-[10px] font-mono text-[var(--t-text-tertiary)]">
                      {{ item.sort_order }}
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-[var(--t-text-primary)]">{{ item.text }}</p>
                      @if (item.initiatives) {
                        <p class="text-[10px] text-[var(--t-accent)] font-bold mt-0.5">
                          {{ item.initiatives.initiative_code }} - {{ item.initiatives.name }}
                        </p>
                      }
                    </div>
                    <button class="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--t-text-tertiary)] hover:text-red-500">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                    </button>
                  </div>
                }
              </div>
            </div>

            <!-- Past Sessions -->
            <div class="card p-6">
              <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Past Sessions</h3>
              <div class="space-y-4">
                @for (s of m.sessions; track s.id) {
                  <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-all cursor-pointer">
                    <div class="flex items-center gap-4">
                      <div class="text-center">
                        <p class="text-xs font-black text-[var(--t-text-primary)]">{{ s.session_date | date:'dd' }}</p>
                        <p class="text-[9px] font-bold uppercase text-[var(--t-text-tertiary)]">{{ s.session_date | date:'MMM' }}</p>
                      </div>
                      <div class="w-px h-8 bg-[var(--t-border)] mx-2"></div>
                      <div>
                        <p class="text-sm font-bold text-[var(--t-text-primary)]">Review Session</p>
                        <div class="flex items-center gap-2 mt-1">
                          @if (s.has_transcript) {
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 font-bold uppercase">Transcript</span>
                          }
                          @if (s.ai_optimised) {
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-500 font-bold uppercase">AI Optimized</span>
                          }
                        </div>
                      </div>
                    </div>
                    <span class="badge badge-green text-[10px]">{{ s.status | uppercase }}</span>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Right: Attendees -->
          <div class="space-y-6">
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Attendees</h3>
                <button class="text-xs text-[var(--t-accent)] font-semibold">Manage</button>
              </div>
              <div class="space-y-4">
                @for (a of m.attendees; track a.id) {
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex items-center justify-center text-xs font-bold text-[var(--t-accent)]">
                      {{ (a.users?.display_name || 'U').substring(0,1) }}
                    </div>
                    <div>
                      <p class="text-xs font-bold text-[var(--t-text-primary)]">{{ a.users?.display_name }}</p>
                      <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ a.users?.role }}</p>
                    </div>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class MeetingDetailComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  
  meeting = signal<any>(null);

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.api.get<any>(`/meetings/${id}`).subscribe(m => this.meeting.set(m));
      }
    });
  }

  startSession() {
    const m = this.meeting();
    if (!m) return;
    
    this.api.post<any>(`/meetings/${m.id}/sessions/start`, {}).subscribe(session => {
      this.router.navigate(['/meetings/sessions', session.id]);
    });
  }
}
