import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

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
            <button (click)="openEdit(m)" class="btn-ghost text-sm" aria-label="Edit meeting series">Edit Series</button>
            <button (click)="startSession()" class="btn-primary text-sm flex items-center gap-2">
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
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ m.workstreams?.name || 'All' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Sessions</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ m.sessions?.length || 0 }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div class="lg:col-span-2 space-y-8">
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Next Agenda</h3>
                <button (click)="showAgendaForm.set(!showAgendaForm())" class="text-xs text-[var(--t-accent)] font-semibold" aria-label="Add agenda item">+ Add Item</button>
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
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-500 font-bold uppercase">AI Optimized</span>
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
            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="editing.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" class="btn-primary text-sm">Save changes</button>
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
  editing = signal(false);
  showAgendaForm = signal(false);
  showAttendeeForm = signal(false);
  showInitiativeForm = signal(false);
  selectedUserId = '';
  selectedInitiativeId = '';
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
    };
    this.editing.set(true);
  }

  saveMeeting() {
    this.api.put<any>(`/meetings/${this.meetingId}`, this.editDraft).subscribe(m => {
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

  startSession() {
    const m = this.meeting();
    if (!m) return;
    
    this.api.post<any>(`/meetings/${m.id}/sessions/start`, {}).subscribe(session => {
      this.router.navigate(['/meetings/sessions', session.id]);
    });
  }
}
