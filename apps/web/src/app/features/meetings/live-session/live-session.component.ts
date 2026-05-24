import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject, forkJoin, interval, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';

type ArtifactType = 'action' | 'decision' | 'risk' | 'assumption' | 'issue';

interface MeetingArtifact {
  id: string;
  artifact_type: ArtifactType;
  title: string;
  description?: string | null;
  status: string;
  priority?: string | null;
  agenda_item_id?: string | null;
  initiative_id?: string | null;
  linked_record_type?: string | null;
  linked_record_id?: string | null;
  users?: { display_name?: string | null } | null;
  initiatives?: { name?: string | null; initiative_code?: string | null } | null;
}

@Component({
  selector: 'app-live-session',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="h-screen flex flex-col overflow-hidden bg-[var(--t-bg)]">
      @if (session(); as s) {
        <header class="h-16 shrink-0 border-b border-[var(--t-border)] bg-[var(--t-surface)] flex items-center justify-between px-6">
          <div class="flex items-center gap-4 min-w-0">
            <a [routerLink]="['/meetings', s.meeting_id]" class="btn-ghost h-9 w-9 p-0" aria-label="Back to meeting">
              <span class="material-icons text-sm">arrow_back</span>
            </a>
            <div class="min-w-0">
              <div class="flex items-center gap-3">
                <h1 class="text-lg font-black truncate text-[var(--t-text-primary)]">{{ s.meetings?.name }}</h1>
                <span class="badge badge-red text-[9px] animate-pulse">Live</span>
              </div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                {{ s.session_date | date:'EEE, MMM d' }} · {{ duration() }} · {{ saveStatus() }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button class="btn-ghost text-xs" (click)="importTranscript()">Import Transcript</button>
            <button class="btn-secondary text-xs" (click)="generateMinutes()">Generate Minutes</button>
            <button class="btn-ghost text-xs" [disabled]="!session()?.minutes_markdown" (click)="sendMinutes()">Send Minutes</button>
            <button class="btn-primary text-xs px-5" (click)="endSession()">Complete Session</button>
          </div>
        </header>

        <main class="flex-1 grid grid-cols-[280px_minmax(0,1fr)_380px] overflow-hidden">
          <aside class="border-r border-[var(--t-border)] bg-[var(--t-surface-raised)]/35 overflow-y-auto">
            <div class="p-4 space-y-5">
              <section>
                <div class="flex items-center justify-between mb-3">
                  <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Agenda</h2>
                  <span class="text-[10px] font-bold text-[var(--t-text-tertiary)]">{{ (s.agenda || []).length }}</span>
                </div>
                <div class="space-y-2">
                  @for (item of s.agenda; track item.id; let i = $index) {
                    <button
                      class="w-full text-left p-3 border transition-colors"
                      [class.bg-[var(--t-accent-soft)]]="activeAgendaIndex() === i"
                      [class.border-[var(--t-accent)]]="activeAgendaIndex() === i"
                      [class.bg-[var(--t-surface)]]="activeAgendaIndex() !== i"
                      [class.border-[var(--t-border)]]="activeAgendaIndex() !== i"
                      (click)="selectAgenda(i)"
                    >
                      <div class="flex items-start gap-2">
                        <span class="text-[10px] font-mono font-black text-[var(--t-accent)]">{{ i + 1 }}</span>
                        <div class="min-w-0">
                          <p class="text-xs font-bold leading-snug text-[var(--t-text-primary)]">{{ item.text }}</p>
                          @if (item.initiatives) {
                            <p class="mt-1 text-[9px] font-black uppercase tracking-wider text-[var(--t-accent)]">
                              {{ item.initiatives.initiative_code }} · {{ item.initiatives.name }}
                            </p>
                          }
                        </div>
                      </div>
                    </button>
                  }
                  @if ((s.agenda || []).length === 0) {
                    <div class="p-4 border border-dashed border-[var(--t-border)] text-xs text-[var(--t-text-secondary)]">
                      No agenda items configured.
                    </div>
                  }
                </div>
              </section>

              <section class="pt-4 border-t border-[var(--t-border)]">
                <div class="flex items-center justify-between mb-3">
                  <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Carry Forward</h2>
                  <span class="text-[10px] font-bold text-[var(--t-amber)]">{{ (s.carry_forward_action_items || []).length }}</span>
                </div>
                <div class="space-y-2">
                  @for (item of s.carry_forward_action_items || []; track item.id) {
                    <div class="p-3 bg-[var(--t-surface)] border border-[var(--t-border)]">
                      <p class="text-xs font-bold text-[var(--t-text-primary)]">{{ item.description }}</p>
                      <p class="mt-1 text-[9px] font-bold uppercase text-[var(--t-text-tertiary)]">
                        {{ item.meeting_sessions?.session_date | date:'MMM d' }} · {{ item.status }}
                      </p>
                    </div>
                  }
                  @if ((s.carry_forward_action_items || []).length === 0) {
                    <p class="text-xs text-[var(--t-text-secondary)]">No open actions from prior sessions.</p>
                  }
                </div>
              </section>
            </div>
          </aside>

          <section class="overflow-y-auto bg-[var(--t-bg)]">
            <div class="p-6 space-y-5">
              <div class="border-b border-[var(--t-border)] pb-4">
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Current Topic</p>
                <h2 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ activeAgenda()?.text || 'Open discussion' }}</h2>
              </div>

              @if (initiativeContext(); as ctx) {
                <div class="grid grid-cols-2 xl:grid-cols-4 gap-3">
                  @for (card of contextCards(); track card.label) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
                      <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
                      <p class="mt-2 text-lg font-black text-[var(--t-text-primary)]">{{ card.value }}</p>
                    </div>
                  }
                </div>

                <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Initiative Summary</h3>
                    <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">{{ ctx.detail?.summary || 'No executive summary recorded.' }}</p>
                    <div class="mt-4 flex flex-wrap gap-2 text-[10px] font-black uppercase">
                      <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">{{ ctx.detail?.stage || 'stage' }}</span>
                      <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">{{ ctx.detail?.priority || 'priority' }}</span>
                      <span class="px-2 py-1 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]">{{ ctx.detail?.owner_name || 'Unassigned' }}</span>
                    </div>
                  </div>

                  <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Brief Financials</h3>
                    <div class="mt-4 grid grid-cols-2 gap-3">
                      @for (row of financialRows(); track row.label) {
                        <div class="bg-[var(--t-surface-raised)] p-3">
                          <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">{{ row.label }}</p>
                          <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ row.value }}</p>
                        </div>
                      }
                    </div>
                  </div>

                  <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Near Milestones</h3>
                    <div class="mt-3 space-y-2">
                      @for (m of (ctx.milestones?.items || []).slice(0, 4); track m.id) {
                        <div class="flex justify-between gap-3 text-xs">
                          <span class="font-bold text-[var(--t-text-primary)] truncate">{{ m.name }}</span>
                          <span class="font-mono text-[var(--t-text-tertiary)]">{{ m.planned_end || 'TBD' }}</span>
                        </div>
                      }
                    </div>
                  </div>

                  <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Open Risks</h3>
                    <div class="mt-3 space-y-2">
                      @for (r of (ctx.risks?.items || []).slice(0, 4); track r.id) {
                        <div class="text-xs">
                          <p class="font-bold text-[var(--t-text-primary)] truncate">{{ r.description }}</p>
                          <p class="text-[9px] uppercase font-black text-[var(--t-text-tertiary)]">{{ r.rating || 'unrated' }} · {{ r.status }}</p>
                        </div>
                      }
                    </div>
                  </div>
                </div>
              } @else {
                <div class="p-12 border border-dashed border-[var(--t-border)] text-center">
                  <p class="text-sm font-bold text-[var(--t-text-secondary)]">Select an agenda item linked to an initiative to load initiative context.</p>
                </div>
              }

              @if (session()?.minutes_markdown) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                  <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-black text-[var(--t-text-primary)]">Draft Minutes</h3>
                    <span class="badge-ghost text-[10px]">{{ session()?.minutes_status || 'draft' }}</span>
                  </div>
                  <textarea [(ngModel)]="minutesDraft" rows="10" class="input-field w-full text-sm font-mono" aria-label="Draft meeting minutes"></textarea>
                  <button class="btn-secondary text-xs mt-3" (click)="saveMinutesDraft()">Save Draft</button>
                </div>
              }
            </div>
          </section>

          <aside class="border-l border-[var(--t-border)] bg-[var(--t-surface-raised)]/35 flex flex-col overflow-hidden">
            <section class="h-[42%] border-b border-[var(--t-border)] flex flex-col">
              <div class="p-4 border-b border-[var(--t-border)]">
                <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Notes</h2>
              </div>
              <textarea
                [(ngModel)]="notes"
                (ngModelChange)="onNotesChange()"
                placeholder="Capture meeting minutes, decisions, and key discussion points..."
                class="flex-1 bg-transparent border-none outline-none resize-none p-4 text-sm leading-6 text-[var(--t-text-primary)] placeholder:text-[var(--t-text-tertiary)]"
              ></textarea>
            </section>

            <section class="flex-1 flex flex-col min-h-0">
              <div class="p-4 border-b border-[var(--t-border)] flex items-center justify-between">
                <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Action Center</h2>
                <span class="text-[10px] font-black text-[var(--t-accent)]">{{ artifacts().length }} total</span>
              </div>

              <div class="p-4 border-b border-[var(--t-border)] space-y-3">
                <div class="grid grid-cols-2 gap-2">
                  <select [(ngModel)]="artifactDraft.artifact_type" class="input-field text-xs" aria-label="Artifact type">
                    <option value="action">Action</option>
                    <option value="decision">Decision</option>
                    <option value="risk">Risk</option>
                    <option value="assumption">Assumption</option>
                    <option value="issue">Issue</option>
                  </select>
                  <select [(ngModel)]="artifactDraft.priority" class="input-field text-xs" aria-label="Artifact priority">
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <textarea
                  [(ngModel)]="newActionItem"
                  (keyup.enter)="addActionItem()"
                  placeholder="Capture a new action item..."
                  class="input-field w-full h-20 resize-none text-xs"
                ></textarea>
                <button
                  class="btn-primary w-full text-xs"
                  [disabled]="!newActionItem.trim()"
                  aria-label="Add action item"
                  (click)="addActionItem()"
                >
                  Add {{ artifactLabel(artifactDraft.artifact_type) }}
                </button>
              </div>

              <div class="flex-1 overflow-y-auto p-4 space-y-3">
                @for (artifact of artifacts(); track artifact.id) {
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3 group">
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-[9px] font-black uppercase tracking-widest" [style.color]="artifactColor(artifact.artifact_type)">
                        {{ artifact.artifact_type }}
                      </span>
                      <button class="opacity-0 group-hover:opacity-100 text-red-500" (click)="deleteArtifact(artifact)" aria-label="Delete action item">
                        <span class="material-icons text-sm">delete_outline</span>
                      </button>
                    </div>
                    <p class="mt-2 text-xs font-bold leading-5 text-[var(--t-text-primary)]">{{ artifact.title }}</p>
                    @if (artifact.description) {
                      <p class="mt-1 text-[11px] leading-4 text-[var(--t-text-secondary)]">{{ artifact.description }}</p>
                    }
                    <div class="mt-3 grid grid-cols-2 gap-2">
                      <select class="input-field text-[10px] h-8" [ngModel]="artifact.status" (ngModelChange)="updateArtifact(artifact, { status: $event })" aria-label="Artifact status">
                        <option value="open">Open</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="noted">Noted</option>
                        <option value="accepted">Accepted</option>
                        <option value="rejected">Rejected</option>
                      </select>
                      <button class="btn-ghost h-8 text-[10px]" (click)="toggleActionItem(artifact)" aria-label="Toggle action item status">
                        Toggle
                      </button>
                    </div>
                  </div>
                }
                @if (artifacts().length === 0) {
                  <div class="p-6 border border-dashed border-[var(--t-border)] text-center text-xs text-[var(--t-text-secondary)]">
                    No artifacts captured yet.
                  </div>
                }
              </div>
            </section>
          </aside>
        </main>
      }
    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; }
  `],
})
export class LiveSessionComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroy$ = new Subject<void>();
  private readonly notesChanged$ = new Subject<string>();

  session = signal<any>(null);
  artifacts = signal<MeetingArtifact[]>([]);
  initiativeContext = signal<any | null>(null);
  activeAgendaIndex = signal(0);
  duration = signal('00:00:00');
  saveStatus = signal('All changes saved');
  notes = '';
  minutesDraft = '';
  transcriptDraft = '';
  newActionItem = '';
  artifactDraft: { artifact_type: ArtifactType; priority: string } = {
    artifact_type: 'action',
    priority: 'medium',
  };

  private startTime = Date.now();

  activeAgenda = computed(() => {
    const agenda = this.session()?.agenda || [];
    return agenda[this.activeAgendaIndex()] || agenda[0] || null;
  });

  contextCards = computed(() => {
    const detail = this.initiativeContext()?.detail || {};
    const summary = this.initiativeContext()?.financials?.summary || {};
    return [
      { label: 'RAG', value: (detail.rag_status || 'unknown').toUpperCase() },
      { label: 'Stage', value: (detail.stage || 'not set').replace('_', ' ') },
      { label: 'Plan Value', value: this.formatCurrency(summary.net_value_plan || summary.gm_uplift_plan || '0') },
      { label: 'Actual Value', value: this.formatCurrency(summary.net_value_actual || summary.gm_uplift_actual || '0') },
    ];
  });

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.loadSession(id);

    interval(1000).pipe(takeUntil(this.destroy$)).subscribe(() => {
      const diff = Math.floor((Date.now() - this.startTime) / 1000);
      const h = Math.floor(diff / 3600).toString().padStart(2, '0');
      const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
      const s = (diff % 60).toString().padStart(2, '0');
      this.duration.set(`${h}:${m}:${s}`);
    });

    this.notesChanged$.pipe(
      debounceTime(1000),
      distinctUntilChanged(),
      takeUntil(this.destroy$),
    ).subscribe(content => this.saveNotes(content));
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadSession(id: string) {
    this.api.get<any>(`/meetings/sessions/${id}`).subscribe(s => {
      this.session.set(s);
      this.notes = s.notes || '';
      this.minutesDraft = s.minutes_markdown || '';
      this.transcriptDraft = s.transcript_text || '';
      this.artifacts.set(s.artifacts || []);
      this.selectAgenda(this.activeAgendaIndex());
    });
  }

  selectAgenda(index: number) {
    this.activeAgendaIndex.set(index);
    const item = (this.session()?.agenda || [])[index];
    const initiativeId = item?.initiative_id;
    if (!initiativeId) {
      this.initiativeContext.set(null);
      return;
    }
    forkJoin({
      detail: this.api.get<any>(`/initiatives/${initiativeId}`).pipe(catchError(() => of(null))),
      financials: this.api.get<any>(`/initiatives/${initiativeId}/financials`).pipe(catchError(() => of(null))),
      risks: this.api.get<any>(`/initiatives/${initiativeId}/risks`).pipe(catchError(() => of({ items: [] }))),
      milestones: this.api.get<any>(`/initiatives/${initiativeId}/milestones`).pipe(catchError(() => of({ items: [] }))),
    }).subscribe(ctx => this.initiativeContext.set(ctx));
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
      error: () => this.saveStatus.set('Error saving'),
    });
  }

  addActionItem() {
    const title = this.newActionItem.trim();
    const session = this.session();
    if (!title || !session?.id) return;
    const active = this.activeAgenda();
    const body = {
      artifact_type: this.artifactDraft.artifact_type,
      title,
      description: title,
      priority: this.artifactDraft.priority,
      status: 'open',
      agenda_item_id: active?.id || null,
      initiative_id: active?.initiative_id || null,
    };
    this.api.post<MeetingArtifact>(`/meetings/sessions/${session.id}/artifacts`, body).subscribe(item => {
      this.artifacts.set([item, ...this.artifacts()]);
      this.newActionItem = '';
      this.loadSession(session.id);
    });
  }

  updateArtifact(artifact: MeetingArtifact, patch: Record<string, string | null>) {
    this.api.put<MeetingArtifact>(`/meeting-artifacts/${artifact.id}`, patch).subscribe(updated => {
      this.artifacts.set(this.artifacts().map(item => item.id === artifact.id ? { ...item, ...updated } : item));
    });
  }

  deleteArtifact(artifact: MeetingArtifact) {
    this.api.delete(`/meeting-artifacts/${artifact.id}`).subscribe(() => {
      this.artifacts.set(this.artifacts().filter(item => item.id !== artifact.id));
      const id = this.session()?.id;
      if (id) this.loadSession(id);
    });
  }

  removeActionItem(id: string) {
    const artifact = this.artifacts().find(item => item.id === id || item.linked_record_id === id);
    if (artifact) this.deleteArtifact(artifact);
  }

  toggleActionItem(item: MeetingArtifact) {
    const status = item.status === 'completed' ? 'open' : 'completed';
    this.updateArtifact(item, { status });
  }

  importTranscript() {
    const id = this.session()?.id;
    if (!id) return;
    this.api.post<any>(`/meetings/sessions/${id}/transcript/import`, {
      transcript_text: this.transcriptDraft || this.notes,
      transcript_source: this.transcriptDraft ? 'manual' : 'notes',
    }).subscribe(s => this.session.set({ ...this.session(), ...s }));
  }

  generateMinutes() {
    const id = this.session()?.id;
    if (!id) return;
    this.api.post<any>(`/meetings/sessions/${id}/minutes/generate`, { force: true }).subscribe(s => {
      this.session.set({ ...this.session(), ...s });
      this.minutesDraft = s.minutes_markdown || '';
    });
  }

  saveMinutesDraft() {
    const id = this.session()?.id;
    if (!id) return;
    this.api.patch<any>(`/meetings/sessions/${id}`, {
      minutes_markdown: this.minutesDraft,
      minutes_status: 'draft',
    }).subscribe(s => this.session.set({ ...this.session(), ...s }));
  }

  sendMinutes() {
    const id = this.session()?.id;
    if (!id) return;
    this.saveMinutesDraft();
    this.api.post<any>(`/meetings/sessions/${id}/minutes/send`, {}).subscribe(s => {
      this.session.set({ ...this.session(), ...s });
    });
  }

  endSession() {
    const id = this.session()?.id;
    if (!id) return;
    this.api.post(`/meetings/sessions/${id}/end`, {}).subscribe(() => {
      this.router.navigate(['/meetings', this.session().meeting_id]);
    });
  }

  financialRows() {
    const summary = this.initiativeContext()?.financials?.summary || {};
    return [
      { label: 'Revenue', value: this.formatCurrency(summary.revenue_plan || summary.revenue_uplift_plan || '0') },
      { label: 'Gross Margin', value: this.formatCurrency(summary.gross_margin_plan || summary.gm_uplift_plan || '0') },
      { label: 'One Time Cost', value: this.formatCurrency(summary.one_off_costs_plan || '0') },
      { label: 'Recurring Cost', value: this.formatCurrency(summary.recurring_costs_plan || '0') },
    ];
  }

  artifactLabel(type: ArtifactType): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  artifactColor(type: ArtifactType): string {
    const colors: Record<ArtifactType, string> = {
      action: 'var(--t-accent)',
      decision: 'var(--t-green)',
      risk: 'var(--t-red)',
      assumption: 'var(--t-amber)',
      issue: 'var(--t-text-primary)',
    };
    return colors[type];
  }

  formatCurrency(value: string | number): string {
    const amount = Number(value) || 0;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  }
}
