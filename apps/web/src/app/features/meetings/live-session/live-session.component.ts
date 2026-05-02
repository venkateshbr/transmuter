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
    <div class="h-screen flex flex-col bg-[var(--t-bg)] overflow-hidden">
      
      @if (session(); as s) {
        <!-- Top Navigation / Header -->
        <header class="h-16 border-b border-[var(--t-border)] bg-[var(--t-surface)] flex items-center justify-between px-8 shrink-0">
          <div class="flex items-center gap-4">
            <a [routerLink]="['/meetings', s.meeting_id]" class="btn-ghost p-2 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </a>
            <div>
              <h1 class="text-lg font-bold text-[var(--t-text-primary)] leading-tight">
                {{ s.meetings?.name }}<span class="text-[var(--t-accent)]">.</span>
              </h1>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                Live Session • {{ s.session_date | date:'mediumDate' }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-8">
            <div class="flex flex-col items-end">
              <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Duration</p>
              <p class="text-sm font-mono font-bold text-[var(--t-accent)]">{{ duration() }}</p>
            </div>
            <button (click)="endSession()" class="btn-primary px-6 py-2 rounded-full text-xs font-bold shadow-lg shadow-purple-500/20 hover:scale-105 active:scale-95 transition-all">
              End Session
            </button>
          </div>
        </header>

        <!-- Main Content Area -->
        <main class="flex-1 flex overflow-hidden">
          
          <!-- Left: Agenda Sidecar -->
          <aside class="w-80 border-r border-[var(--t-border)] flex flex-col shrink-0 bg-[var(--t-surface-raised)]/30">
            <div class="p-6 border-b border-[var(--t-border)]">
              <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Agenda</h3>
            </div>
            <div class="flex-1 overflow-y-auto p-4 space-y-2">
              @for (item of s.agenda; track item.id; let i = $index) {
                <div [class.bg-[var(--t-surface-raised)]]="activeAgendaIndex() === i"
                     [class.border-[var(--t-accent)]]="activeAgendaIndex() === i"
                     class="p-4 rounded-xl border border-[var(--t-border)] transition-all cursor-pointer group"
                     (click)="activeAgendaIndex.set(i)">
                  <div class="flex items-start gap-3">
                    <span class="text-[10px] font-mono text-[var(--t-text-tertiary)] mt-0.5">{{ i + 1 }}</span>
                    <p class="text-xs font-bold leading-relaxed text-[var(--t-text-primary)]">{{ item.text }}</p>
                  </div>
                </div>
              }
            </div>
          </aside>

          <!-- Center: Live Notes -->
          <section class="flex-1 flex flex-col min-w-0 bg-[var(--t-bg)]">
            <div class="p-6 border-b border-[var(--t-border)] flex justify-between items-center bg-[var(--t-surface)]">
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Meeting Notes</h3>
              </div>
              <span class="text-[10px] text-[var(--t-text-tertiary)] font-bold italic">{{ saveStatus() }}</span>
            </div>
            <div class="flex-1 p-8 overflow-y-auto">
              <textarea 
                [(ngModel)]="notes" 
                (ngModelChange)="onNotesChange()"
                placeholder="Start typing meeting notes here..."
                class="w-full h-full bg-transparent border-none outline-none resize-none text-base leading-relaxed text-[var(--t-text-primary)] placeholder-[var(--t-text-tertiary)]/50 font-serif"
              ></textarea>
            </div>
          </section>

          <!-- Right: Live Action Items -->
          <aside class="w-96 border-l border-[var(--t-border)] flex flex-col shrink-0 bg-[var(--t-surface-raised)]/30">
            <div class="p-6 border-b border-[var(--t-border)]">
              <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Action Items</h3>
            </div>
            
            <!-- Quick Add -->
            <div class="p-4 border-b border-[var(--t-border)] bg-[var(--t-surface)]">
              <div class="relative">
                <input 
                  type="text" 
                  [(ngModel)]="newActionItem"
                  (keyup.enter)="addActionItem()"
                  placeholder="Capture new action item..."
                  class="w-full pl-4 pr-10 py-2.5 rounded-xl bg-[var(--t-bg-page)] border border-[var(--t-border)] text-xs focus:border-[var(--t-accent)] outline-none transition-all"
                >
                <button (click)="addActionItem()" class="absolute right-2 top-1.5 p-1 text-[var(--t-accent)] hover:bg-[var(--t-accent)]/10 rounded-lg transition-all">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
                </button>
              </div>
            </div>

            <!-- List -->
            <div class="flex-1 overflow-y-auto p-4 space-y-3">
              @for (ai of actionItems(); track ai.id) {
                <div class="card p-3 border-l-4 border-l-[var(--t-accent)] animate-slide-in">
                  <p class="text-xs font-medium text-[var(--t-text-primary)] leading-relaxed">{{ ai.description }}</p>
                  <div class="flex items-center justify-between mt-2">
                    <span class="badge badge-purple text-[8px] uppercase tracking-tighter">NEW</span>
                    <button class="text-[var(--t-text-tertiary)] hover:text-red-500">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                    </button>
                  </div>
                </div>
              }
            </div>
          </aside>

        </main>
      } @else {
        <div class="flex-1 flex items-center justify-center">
          <div class="flex flex-col items-center gap-4">
            <div class="w-12 h-12 border-4 border-[var(--t-accent)] border-t-transparent rounded-full animate-spin"></div>
            <p class="text-sm font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">Initializing Session...</p>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; }
    textarea::placeholder { opacity: 0.3; }
    .animate-slide-in {
      animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slideIn {
      from { transform: translateX(20px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
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

  endSession() {
    const id = this.session()?.id;
    if (!id) return;

    if (confirm('Are you sure you want to end this session?')) {
      this.api.post(`/meetings/sessions/${id}/end`, {}).subscribe(() => {
        this.router.navigate(['/meetings', this.session().meeting_id]);
      });
    }
  }
}
