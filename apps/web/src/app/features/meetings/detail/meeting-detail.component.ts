import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-meeting-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      @if (meeting(); as m) {
        <div class="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
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
            <button (click)="createMicrosoftEvent()" class="btn-secondary text-sm flex items-center gap-2" aria-label="Create Microsoft Teams invite">
              <span class="material-icons text-sm">video_call</span>
              Teams Invite
            </button>
            <button (click)="openEdit(m)" class="btn-ghost text-sm" aria-label="Edit meeting series">Edit Series</button>
            <button (click)="openStartSession()" class="btn-primary text-sm flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Start Session
            </button>
          </div>
        </div>

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
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ meetingWorkstreamLabel(m) }}</p>
          </div>
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Sessions</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ m.sessions?.length || 0 }}</p>
          </div>
        </div>

        @if ((m.external_events || []).length > 0) {
          <div class="card p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Microsoft 365</p>
              @for (event of m.external_events; track event.id) {
                <p class="mt-1 text-sm font-bold text-[var(--t-text-primary)]">
                  {{ event.sync_status | titlecase }}
                  @if (event.join_url) {
                    · <a [href]="event.join_url" target="_blank" rel="noreferrer" class="text-[var(--t-accent)] hover:underline">Join Teams</a>
                  }
                </p>
                @if (event.sync_error) {
                  <p class="mt-1 text-xs text-[var(--t-text-secondary)]">{{ event.sync_error }}</p>
                }
              }
            </div>
            <button (click)="createMicrosoftEvent()" class="btn-ghost text-xs">Sync Invite</button>
          </div>
        }

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div class="lg:col-span-2 space-y-8">
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Next Agenda</h3>
                <div class="flex items-center gap-3">
                  <button (click)="fetchAgendaSuggestions()" class="text-xs text-[var(--t-accent)] font-semibold" aria-label="Suggest agenda items">Suggest</button>
                  <button (click)="showAgendaForm.set(!showAgendaForm())" class="text-xs text-[var(--t-accent)] font-semibold" aria-label="Add agenda item">+ Add Item</button>
                </div>
              </div>

              @if (showAgendaForm()) {
                <form (ngSubmit)="addAgendaItem()" class="mb-5 grid grid-cols-1 md:grid-cols-[1fr_220px_auto] gap-3">
                  <input [(ngModel)]="agendaDraft.text" name="agenda_text" required class="input-field text-sm" placeholder="Agenda topic" aria-label="Agenda topic" />
                  <select [(ngModel)]="agendaDraft.initiative_id" name="agenda_initiative" class="input-field text-sm" aria-label="Agenda initiative">
                    <option value="">No initiative</option>
                    @for (i of initiatives(); track i.id) {
                      <option [value]="i.id">{{ i.initiative_code }} - {{ i.name }}</option>
                    }
                  </select>
                  <button type="submit" class="btn-primary text-sm">Add</button>
                </form>
              }

              @if (suggestionsError()) {
                <p class="mb-3 text-sm text-red-500">{{ suggestionsError() }}</p>
              }

              @if (agendaSuggestions().length) {
                <div class="mb-5 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 space-y-3">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-xs font-black uppercase tracking-widest text-[var(--t-text-secondary)]">AI agenda suggestions</p>
                      <p class="text-xs text-[var(--t-text-tertiary)]">Review, edit, reject, then save accepted items.</p>
                    </div>
                    <button (click)="saveAcceptedSuggestions()" [disabled]="savingSuggestions()" class="btn-primary text-xs">
                      {{ savingSuggestions() ? 'Saving...' : 'Save accepted' }}
                    </button>
                  </div>
                  @for (suggestion of agendaSuggestions(); track suggestion.client_id) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3">
                      <div class="flex items-start gap-3">
                        <input
                          type="checkbox"
                          [checked]="suggestion.accepted"
                          (change)="toggleSuggestionAccepted(suggestion.client_id, $any($event.target).checked)"
                          class="mt-2 h-4 w-4"
                          [attr.aria-label]="'Accept agenda suggestion ' + suggestion.text"
                        />
                        <div class="min-w-0 flex-1 space-y-2">
                          <textarea [(ngModel)]="suggestion.text" rows="2" class="input-field w-full text-sm resize-none" aria-label="Edit agenda suggestion"></textarea>
                          <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                            <p class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">{{ suggestion.source_type }} · {{ suggestion.rationale }}</p>
                            <button type="button" (click)="rejectSuggestion(suggestion.client_id)" class="btn-ghost text-[10px]" aria-label="Reject agenda suggestion">Reject</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  }
                </div>
              }

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
                    <button (click)="deleteAgendaItem(item.id)" class="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--t-text-tertiary)] hover:text-red-500" aria-label="Delete agenda item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                    </button>
                  </div>
                }
                @if ((m.agenda || []).length === 0) {
                  <div class="p-5 rounded-xl border border-dashed border-[var(--t-border)] text-sm text-[var(--t-text-secondary)]">
                    No agenda items yet.
                  </div>
                }
              </div>
            </div>

            <div class="card p-6">
              <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Past Sessions</h3>
              <div class="space-y-4">
                @for (s of m.sessions; track s.id) {
                  <div [routerLink]="['/meetings/sessions', s.id]" class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-all cursor-pointer">
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
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)] font-bold uppercase">AI Optimized</span>
                          }
                        </div>
                      </div>
                    </div>
                    <span class="badge badge-green text-[10px]">{{ s.status | uppercase }}</span>
                  </div>
                }
                @if ((m.sessions || []).length === 0) {
                  <div class="p-5 rounded-xl border border-dashed border-[var(--t-border)] text-sm text-[var(--t-text-secondary)]">
                    No sessions have been started.
                  </div>
                }
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Attendees</h3>
                <button (click)="showAttendeeForm.set(!showAttendeeForm())" class="text-xs text-[var(--t-accent)] font-semibold" aria-label="Add attendee">+ Add</button>
              </div>
              @if (showAttendeeForm()) {
                <form (ngSubmit)="addAttendee()" class="mb-5 flex gap-2">
                  <select [(ngModel)]="selectedUserId" name="selected_user" required class="input-field text-sm min-w-0 flex-1" aria-label="Select attendee">
                    @for (u of users(); track u.id) {
                      <option [value]="u.id">{{ u.display_name || u.email }}</option>
                    }
                  </select>
                  <button type="submit" class="btn-primary text-sm">Add</button>
                </form>
              }
              <div class="space-y-4">
                @for (a of m.attendees; track a.id) {
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex items-center justify-center text-xs font-bold text-[var(--t-accent)]">
                      {{ (a.users?.display_name || 'U').substring(0,1) }}
                    </div>
                    <div class="min-w-0 flex-1">
                      <p class="text-xs font-bold text-[var(--t-text-primary)]">{{ a.users?.display_name }}</p>
                      <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ a.users?.role }}</p>
                    </div>
                    <button (click)="deleteAttendee(a.id)" class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-red-500 hover:bg-red-500/10 transition-all" aria-label="Remove attendee">
                      <span class="material-icons text-sm">close</span>
                    </button>
                  </div>
                }
              </div>
            </div>

            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Linked Initiatives</h3>
                <button (click)="showInitiativeForm.set(!showInitiativeForm())" class="text-xs text-[var(--t-accent)] font-semibold" aria-label="Link initiative">+ Link</button>
              </div>
              @if (showInitiativeForm()) {
                <form (ngSubmit)="addInitiative()" class="mb-5 flex gap-2">
                  <select [(ngModel)]="selectedInitiativeId" name="selected_initiative" required class="input-field text-sm min-w-0 flex-1" aria-label="Select initiative">
                    @for (i of initiatives(); track i.id) {
                      <option [value]="i.id">{{ i.initiative_code }} - {{ i.name }}</option>
                    }
                  </select>
                  <button type="submit" class="btn-primary text-sm">Link</button>
                </form>
              }
              <div class="space-y-3">
                @for (link of m.initiatives; track link.id) {
                  <div class="flex items-center justify-between gap-3 p-3 rounded-xl border border-[var(--t-border)]">
                    <div class="min-w-0">
                      <p class="text-xs font-bold text-[var(--t-text-primary)] truncate">{{ link.initiatives?.name }}</p>
                      <p class="text-[10px] text-[var(--t-accent)] font-bold">{{ link.initiatives?.initiative_code }}</p>
                    </div>
                    <button (click)="deleteInitiative(link.id)" class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-red-500 hover:bg-red-500/10 transition-all" aria-label="Unlink initiative">
                      <span class="material-icons text-sm">link_off</span>
                    </button>
                  </div>
                }
                @if ((m.initiatives || []).length === 0) {
                  <p class="text-sm text-[var(--t-text-secondary)]">No linked initiatives.</p>
                }
              </div>
            </div>
          </div>
        </div>
      }

      @if (editing()) {
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
          <form (ngSubmit)="saveMeeting()" class="card w-full max-w-xl p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Edit meeting series</h2>
                <p class="text-sm text-[var(--t-text-secondary)] mt-1">Changes save to the real meetings API.</p>
              </div>
              <button type="button" (click)="editing.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close edit meeting dialog">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <label>
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Name</span>
              <input [(ngModel)]="editDraft.name" name="edit_name" required class="input-field w-full" aria-label="Meeting name" />
            </label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Scope</span>
                <select [(ngModel)]="editDraft.scope" name="edit_scope" class="input-field w-full" aria-label="Meeting scope">
                  <option value="all">All</option>
                  <option value="workstream">Workstream</option>
                  <option value="initiative">Initiative</option>
                </select>
              </label>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Recurrence</span>
                <select [(ngModel)]="editDraft.recurrence" name="edit_recurrence" class="input-field w-full" aria-label="Meeting recurrence">
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Biweekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>
            </div>
            <label>
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Description</span>
              <textarea [(ngModel)]="editDraft.description" name="edit_description" rows="3" class="input-field w-full resize-none" aria-label="Meeting description"></textarea>
            </label>
            <fieldset class="border border-[var(--t-border)] p-3">
              <legend class="px-1 text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)]">Workstreams</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                @for (ws of workstreams(); track ws.id) {
                  <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-primary)]">
                    <input
                      type="checkbox"
                      [checked]="editDraft.workstream_ids?.includes(ws.id)"
                      (change)="toggleEditWorkstream(ws.id, $any($event.target).checked)"
                      class="h-4 w-4"
                      [attr.aria-label]="'Select workstream ' + ws.name"
                    />
                    <span>{{ ws.name }}</span>
                  </label>
                }
              </div>
            </fieldset>
            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="editing.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" class="btn-primary text-sm">Save changes</button>
            </div>
          </form>
        </div>
      }

      @if (startingSession()) {
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
          <form (ngSubmit)="startSession()" class="card w-full max-w-md p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Start session</h2>
                <p class="text-sm text-[var(--t-text-secondary)] mt-1">Choose the review date to start or resume.</p>
              </div>
              <button type="button" (click)="startingSession.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close start session dialog">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <label>
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Session Date</span>
              <input [(ngModel)]="startSessionDate" name="session_date" type="date" required class="input-field w-full" aria-label="Session date" />
            </label>
            @if (startSessionError()) {
              <p class="text-sm text-red-500">{{ startSessionError() }}</p>
            }
            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="startingSession.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" class="btn-primary text-sm">Start</button>
            </div>
          </form>
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
  users = signal<any[]>([]);
  initiatives = signal<any[]>([]);
  workstreams = signal<any[]>([]);
  agendaSuggestions = signal<any[]>([]);
  editing = signal(false);
  startingSession = signal(false);
  savingSuggestions = signal(false);
  suggestionsError = signal<string | null>(null);
  startSessionError = signal<string | null>(null);
  showAgendaForm = signal(false);
  showAttendeeForm = signal(false);
  showInitiativeForm = signal(false);
  selectedUserId = '';
  selectedInitiativeId = '';
  startSessionDate = this.todayLocal();
  agendaDraft = { text: '', initiative_id: '' };
  editDraft: any = {};
  private meetingId = '';

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.meetingId = id;
        this.loadMeeting();
      }
    });
    this.api.get<any>('/users').subscribe(res => {
      const users = res.data || [];
      this.users.set(users);
      this.selectedUserId = users[0]?.id || '';
    });
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe(res => {
      const initiatives = res.items || [];
      this.initiatives.set(initiatives);
      this.selectedInitiativeId = initiatives[0]?.id || '';
    });
    this.api.get<any>('/workstreams').subscribe(res => {
      this.workstreams.set(res.items || res.data || []);
    });
  }

  loadMeeting() {
    this.api.get<any>(`/meetings/${this.meetingId}`).subscribe(m => this.meeting.set(m));
  }

  openEdit(meeting: any) {
    this.editDraft = {
      name: meeting.name || '',
      scope: meeting.scope || 'all',
      recurrence: meeting.recurrence || 'weekly',
      description: meeting.description || '',
      workstream_ids: (Array.isArray(meeting.workstreams) ? meeting.workstreams : [])
        .map((ws: any) => ws.id)
        .filter(Boolean),
    };
    this.editing.set(true);
  }

  saveMeeting() {
    const payload = {
      ...this.editDraft,
      workstream_id: this.editDraft.workstream_ids?.[0] || null,
    };
    this.api.put<any>(`/meetings/${this.meetingId}`, payload).subscribe(m => {
      this.meeting.set(m);
      this.editing.set(false);
    });
  }

  addAgendaItem() {
    if (!this.agendaDraft.text.trim()) return;
    this.api.post<any>(`/meetings/${this.meetingId}/agenda`, {
      text: this.agendaDraft.text.trim(),
      initiative_id: this.agendaDraft.initiative_id || null,
    }).subscribe(() => {
      this.agendaDraft = { text: '', initiative_id: '' };
      this.showAgendaForm.set(false);
      this.loadMeeting();
    });
  }

  deleteAgendaItem(itemId: string) {
    this.api.delete(`/meetings/${this.meetingId}/agenda/${itemId}`).subscribe(() => this.loadMeeting());
  }

  addAttendee() {
    if (!this.selectedUserId) return;
    this.api.post<any>(`/meetings/${this.meetingId}/attendees`, { user_id: this.selectedUserId }).subscribe(() => {
      this.showAttendeeForm.set(false);
      this.loadMeeting();
    });
  }

  deleteAttendee(attendeeId: string) {
    this.api.delete(`/meetings/${this.meetingId}/attendees/${attendeeId}`).subscribe(() => this.loadMeeting());
  }

  addInitiative() {
    if (!this.selectedInitiativeId) return;
    this.api.post<any>(`/meetings/${this.meetingId}/initiatives`, { initiative_id: this.selectedInitiativeId }).subscribe(() => {
      this.showInitiativeForm.set(false);
      this.loadMeeting();
    });
  }

  deleteInitiative(linkId: string) {
    this.api.delete(`/meetings/${this.meetingId}/initiatives/${linkId}`).subscribe(() => this.loadMeeting());
  }

  openStartSession() {
    const m = this.meeting();
    if (!m) return;
    this.startSessionDate = this.todayLocal();
    this.startSessionError.set(null);
    this.startingSession.set(true);
  }

  startSession() {
    const m = this.meeting();
    if (!m || !this.startSessionDate) return;

    this.api.post<any>(`/meetings/${m.id}/sessions/start`, {
      session_date: this.startSessionDate,
    }).subscribe({
      next: session => {
        this.startingSession.set(false);
        this.router.navigate(['/meetings/sessions', session.id]);
      },
      error: err => this.startSessionError.set(err.error?.detail || 'Could not start session.'),
    });
  }

  createMicrosoftEvent() {
    const m = this.meeting();
    if (!m) return;
    this.api.post<any>(`/meetings/${m.id}/external-events/microsoft`, {
      organizer_email: null,
      time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    }).subscribe(() => this.loadMeeting());
  }

  fetchAgendaSuggestions() {
    this.suggestionsError.set(null);
    this.api.post<any>(`/meetings/${this.meetingId}/agenda/suggestions`, {}).subscribe({
      next: res => {
        const items = (res.items || []).map((item: any, index: number) => ({
          ...item,
          client_id: `${Date.now()}-${index}`,
          accepted: true,
        }));
        this.agendaSuggestions.set(items);
        if (!items.length) this.suggestionsError.set('No agenda suggestions were available.');
      },
      error: err => this.suggestionsError.set(err.error?.detail || 'Could not generate agenda suggestions.'),
    });
  }

  toggleSuggestionAccepted(clientId: string, accepted: boolean): void {
    this.agendaSuggestions.set(this.agendaSuggestions().map(item =>
      item.client_id === clientId ? { ...item, accepted } : item
    ));
  }

  rejectSuggestion(clientId: string): void {
    this.agendaSuggestions.set(this.agendaSuggestions().filter(item => item.client_id !== clientId));
  }

  saveAcceptedSuggestions() {
    const accepted = this.agendaSuggestions()
      .filter(item => item.accepted && String(item.text || '').trim())
      .map(item => ({
        text: String(item.text).trim(),
        initiative_id: item.initiative_id || null,
      }));
    if (!accepted.length) {
      this.suggestionsError.set('Accept at least one agenda suggestion before saving.');
      return;
    }
    this.savingSuggestions.set(true);
    forkJoin(accepted.map(item => this.api.post<any>(`/meetings/${this.meetingId}/agenda`, item))).subscribe({
      next: () => {
        this.savingSuggestions.set(false);
        this.agendaSuggestions.set([]);
        this.loadMeeting();
      },
      error: err => {
        this.savingSuggestions.set(false);
        this.suggestionsError.set(err.error?.detail || 'Could not save accepted agenda suggestions.');
      },
    });
  }

  toggleEditWorkstream(workstreamId: string, checked: boolean): void {
    const ids = new Set<string>(this.editDraft.workstream_ids || []);
    if (checked) ids.add(workstreamId);
    else ids.delete(workstreamId);
    this.editDraft.workstream_ids = Array.from(ids);
    if (this.editDraft.workstream_ids.length) this.editDraft.scope = 'workstream';
  }

  meetingWorkstreamLabel(meeting: any): string {
    const workstreams = Array.isArray(meeting.workstreams) ? meeting.workstreams : [];
    if (!workstreams.length) return 'All';
    return workstreams.map((ws: any) => ws.name || 'Workstream').join(', ');
  }

  private todayLocal(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }
}
