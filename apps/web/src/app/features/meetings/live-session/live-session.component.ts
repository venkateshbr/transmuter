import { Component, OnInit, inject, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, interval } from 'rxjs';
import { takeUntil, debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-live-session',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="h-screen flex flex-col bg-[var(--t-bg)] overflow-hidden font-sans">
      
      @if (session(); as s) {
        <!-- Premium Glass Header -->
        <header class="h-20 border-b border-[var(--t-border)] bg-[var(--t-surface)]/80 backdrop-blur-md flex items-center justify-between px-10 shrink-0 z-50">
          <div class="flex items-center gap-6">
            <a [routerLink]="['/meetings', s.meeting_id]" class="w-10 h-10 flex items-center justify-center rounded-xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] hover:border-[var(--t-accent)] transition-all">
              <span class="material-icons text-[var(--t-text-secondary)]">arrow_back</span>
            </a>
            <div>
              <div class="flex items-center gap-3">
                <h1 class="text-xl font-black text-[var(--t-text-primary)] tracking-tight">
                  {{ s.meetings?.name }}
                </h1>
                <span class="badge badge-purple animate-pulse">LIVE</span>
              </div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] mt-1 flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-[var(--t-accent)]"></span>
                {{ s.session_date | date:'EEEE, MMM d' }} • TRANSFORMATION STEERING
              </p>
            </div>
          </div>

          <div class="flex items-center gap-10">
            <!-- Sentiment Gauge -->
            <div class="hidden lg:flex items-center gap-4 px-6 border-x border-[var(--t-border)] h-full">
               <div class="flex flex-col items-end">
                 <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Sentiment</p>
                 <p class="text-xs font-black text-green-500 uppercase">Constructive</p>
               </div>
               <div class="w-16 h-8 bg-[var(--t-border)] rounded-t-full relative overflow-hidden">
                 <div class="absolute bottom-0 left-0 w-full h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 opacity-30"></div>
                 <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-0.5 h-full bg-[var(--t-accent)] origin-bottom rotate-[45deg] transition-transform duration-1000"></div>
               </div>
            </div>

            <div class="flex flex-col items-end">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Session Clock</p>
              <p class="text-2xl font-mono font-black text-[var(--t-accent)] tabular-nums">{{ duration() }}</p>
            </div>
            
            <button (click)="endSession()" class="btn-primary px-8 py-3 rounded-2xl text-xs font-black shadow-xl shadow-purple-500/20 hover:scale-[1.02] active:scale-95 transition-all">
              Complete Session
            </button>
          </div>
        </header>

        <!-- Main Content Area -->
        <main class="flex-1 flex overflow-hidden">
          
          <!-- Left: Agenda & AI Scribe -->
          <aside class="w-80 border-r border-[var(--t-border)] flex flex-col shrink-0 bg-[var(--t-surface-raised)]/30 backdrop-blur-sm">
            <div class="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
              
              <!-- Agenda -->
              <section class="space-y-4">
                <h3 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] flex items-center gap-2">
                  <span class="material-icons text-xs">list_alt</span>
                  Agenda
                </h3>
                <div class="space-y-3">
                  @for (item of s.agenda; track item.id; let i = $index) {
                    <div [class.bg-[var(--t-accent-soft)]]="activeAgendaIndex() === i"
                         [class.border-[var(--t-accent)]]="activeAgendaIndex() === i"
                         class="p-4 rounded-2xl border border-[var(--t-border)] bg-[var(--t-surface)] transition-all cursor-pointer hover:border-[var(--t-accent)]/50 group"
                         (click)="activeAgendaIndex.set(i)">
                      <div class="flex items-start gap-3">
                        <span class="text-[10px] font-black text-[var(--t-accent)] mt-0.5">{{ (i + 1).toString().padStart(2, '0') }}</span>
                        <p class="text-[11px] font-bold leading-relaxed text-[var(--t-text-primary)]">{{ item.text }}</p>
                      </div>
                    </div>
                  }
                </div>
              </section>

              <section class="space-y-4 pt-8 border-t border-[var(--t-border)]">
                <h3 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] flex items-center gap-2">
                  <span class="material-icons text-xs">fact_check</span>
                  Session Controls
                </h3>
                <div class="p-4 rounded-2xl border border-[var(--t-border)] bg-[var(--t-surface)]">
                  <p class="text-xs font-medium leading-relaxed text-[var(--t-text-secondary)]">Decisions, risks, actions</p>
                </div>
              </section>
            </div>
          </aside>

          <!-- Center: Dynamic Notes Editor -->
          <section class="flex-1 flex flex-col min-w-0 bg-[var(--t-bg)] relative">
            <div class="absolute top-6 right-6 z-10 flex items-center gap-3">
               <span class="text-[9px] font-bold uppercase text-[var(--t-text-tertiary)] italic">{{ saveStatus() }}</span>
               <div class="w-2 h-2 rounded-full" [class.bg-green-500]="saveStatus().includes('saved')" [class.bg-amber-500]="saveStatus().includes('Saving')"></div>
            </div>

            <div class="flex-1 p-12 overflow-y-auto custom-scrollbar">
              <div class="max-w-4xl mx-auto h-full">
                <textarea 
                  [(ngModel)]="notes" 
                  (ngModelChange)="onNotesChange()"
                  placeholder="Capture meeting minutes, decisions, and key discussion points..."
                  class="w-full h-full bg-transparent border-none outline-none resize-none text-xl leading-loose text-[var(--t-text-primary)] placeholder-[var(--t-text-tertiary)]/30 font-medium font-serif"
                ></textarea>
              </div>
            </div>

            <!-- Bottom Actions Bar -->
            <div class="h-16 border-t border-[var(--t-border)] bg-[var(--t-surface)]/50 backdrop-blur-sm flex items-center px-10 gap-6 shrink-0">
	               <p class="text-[10px] font-bold text-[var(--t-text-tertiary)]">Session notes</p>
            </div>
          </section>

          <!-- Right: Intelligent Action Center -->
          <aside class="w-96 border-l border-[var(--t-border)] flex flex-col shrink-0 bg-[var(--t-surface-raised)]/30 backdrop-blur-sm">
            <div class="p-6 border-b border-[var(--t-border)] flex justify-between items-center">
              <h3 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] flex items-center gap-2">
                <span class="material-icons text-xs">task_alt</span>
                Action Center
              </h3>
              <span class="text-[10px] font-black px-2 py-0.5 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                {{ actionItems().length }} TOTAL
              </span>
            </div>
            
            <!-- List -->
            <div class="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
              @for (ai of actionItems(); track ai.id) {
                <div class="card p-5 border-l-4 border-l-[var(--t-accent)] bg-[var(--t-surface)] animate-slide-in relative group/card">
                  <div class="flex justify-between items-start mb-2">
	                    <button
                        (click)="toggleActionItem(ai)"
                        class="text-[8px] font-black uppercase tracking-tighter px-2 py-0.5 rounded bg-[var(--t-surface-raised)] text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)]"
                        aria-label="Toggle action item status">
	                      {{ ai.status }}
	                    </button>
	                    <button (click)="removeActionItem(ai.id)" class="opacity-0 group-hover/card:opacity-100 text-red-500 transition-opacity" aria-label="Delete action item">
	                      <span class="material-icons text-xs">close</span>
	                    </button>
                  </div>
                  <p class="text-xs font-bold text-[var(--t-text-primary)] leading-relaxed">{{ ai.description }}</p>
                  <div class="mt-4 pt-4 border-t border-[var(--t-border)]/50 flex items-center justify-between">
                     <div class="flex items-center gap-2">
                        <div class="w-5 h-5 rounded-full bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] flex items-center justify-center text-[8px] text-white font-black">
                          {{ (ai.owner_name || 'U').substring(0,1) }}
                        </div>
                        <span class="text-[9px] font-bold text-[var(--t-text-tertiary)]">{{ ai.owner_name || 'Unassigned' }}</span>
                     </div>
                     <span class="text-[8px] font-mono text-[var(--t-text-tertiary)]">Due ASAP</span>
                  </div>
                </div>
              }

              @if (actionItems().length === 0) {
                <div class="py-12 text-center border-2 border-dashed border-[var(--t-border)] rounded-3xl opacity-40">
                   <span class="material-icons text-3xl mb-2">add_task</span>
                   <p class="text-[10px] font-bold uppercase tracking-widest">No actions captured</p>
                </div>
              }
            </div>

            <!-- Enhanced Quick Add -->
            <div class="p-6 border-t border-[var(--t-border)] bg-[var(--t-surface)]">
              <div class="relative group">
                <textarea 
                  [(ngModel)]="newActionItem"
                  (keyup.enter)="addActionItem()"
                  placeholder="Capture a new action item..."
                  class="w-full pl-4 pr-12 py-3 rounded-2xl bg-[var(--t-bg-page)] border border-[var(--t-border)] text-xs focus:border-[var(--t-accent)] outline-none transition-all resize-none h-20"
                ></textarea>
                <button (click)="addActionItem()" 
                        [disabled]="!newActionItem.trim()"
                        aria-label="Add action item"
                        class="absolute right-3 bottom-3 w-8 h-8 rounded-xl bg-[var(--t-accent)] text-white flex items-center justify-center shadow-lg shadow-purple-500/20 disabled:opacity-50 disabled:shadow-none hover:scale-105 active:scale-95 transition-all">
                  <span class="material-icons text-sm">send</span>
                </button>
              </div>
            </div>
          </aside>

        </main>
      } @else {
        <div class="flex-1 flex items-center justify-center bg-[var(--t-bg)]">
          <div class="flex flex-col items-center gap-6">
            <div class="relative">
              <div class="w-20 h-20 border-4 border-[var(--t-accent-soft)] rounded-full animate-pulse"></div>
              <div class="absolute inset-0 w-20 h-20 border-4 border-t-[var(--t-accent)] rounded-full animate-spin"></div>
            </div>
            <div class="text-center">
              <p class="text-xs font-black uppercase tracking-widest text-[var(--t-text-primary)]">Syncing Workspace</p>
              <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] mt-1">Initializing AI Agent Context...</p>
            </div>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; }
    textarea::placeholder { opacity: 0.3; }
    .animate-slide-in {
      animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @keyframes slideIn {
      from { transform: translateX(30px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    .custom-scrollbar::-webkit-scrollbar { width: 4px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--t-border); border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--t-accent); }
  `]
})
export class LiveSessionComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroy$ = new Subject<void>();

  session = signal<any>(null);
  notes = '';
  newActionItem = '';
  actionItems = signal<any[]>([]);
  activeAgendaIndex = signal(0);
  duration = signal('00:00:00');
  saveStatus = signal('All changes saved');

  private startTime = Date.now();
  private notesChanged$ = new Subject<string>();

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadSession(id);
    }

    // Timer
    interval(1000).pipe(takeUntil(this.destroy$)).subscribe(() => {
      const diff = Math.floor((Date.now() - this.startTime) / 1000);
      const h = Math.floor(diff / 3600).toString().padStart(2, '0');
      const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
      const s = (diff % 60).toString().padStart(2, '0');
      this.duration.set(`${h}:${m}:${s}`);
    });

    // Auto-save notes
    this.notesChanged$.pipe(
      debounceTime(1000),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(content => {
      this.saveNotes(content);
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadSession(id: string) {
    this.api.get<any>(`/meetings/sessions/${id}`).subscribe(s => {
      this.session.set(s);
      this.notes = s.notes || '';
      this.actionItems.set(s.action_items || []);
    });
  }

  onNotesChange() {
    this.saveStatus.set('Saving...');
    this.notesChanged$.next(this.notes);
  }

  saveNotes(content: string) {
    const id = this.session()?.id;
    if (!id) return;
    
    this.api.patch(`/meetings/sessions/${id}`, { notes: content }).subscribe({
      next: () => this.saveStatus.set('All changes saved'),
      error: () => this.saveStatus.set('Error saving!')
    });
  }

  addActionItem() {
    if (!this.newActionItem.trim()) return;
    const sessionId = this.session()?.id;
    if (!sessionId) return;

    const payload = {
      description: this.newActionItem,
      priority: 'medium',
      status: 'open'
    };

    this.api.post<any>(`/meetings/sessions/${sessionId}/action-items`, payload).subscribe(item => {
      this.actionItems.set([...this.actionItems(), item]);
      this.newActionItem = '';
    });
  }

  removeActionItem(id: string) {
    this.api.delete(`/action-items/${id}`).subscribe(() => {
      this.actionItems.set(this.actionItems().filter(ai => ai.id !== id));
    });
  }

  toggleActionItem(item: any) {
    const status = item.status === 'completed' ? 'open' : 'completed';
    this.api.put<any>(`/action-items/${item.id}`, { status }).subscribe(updated => {
      this.actionItems.set(this.actionItems().map(ai => ai.id === item.id ? updated : ai));
    });
  }

  endSession() {
    const id = this.session()?.id;
    if (!id) return;

    this.api.post(`/meetings/sessions/${id}/end`, {}).subscribe(() => {
      this.router.navigate(['/meetings', this.session().meeting_id]);
    });
  }
}
