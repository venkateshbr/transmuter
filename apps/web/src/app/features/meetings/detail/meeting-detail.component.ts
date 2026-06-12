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
            <button (click)="openMicrosoftInvite()" class="btn-secondary text-sm flex items-center gap-2" aria-label="Create Microsoft Teams invite">
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
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ recurrenceLabel(m.recurrence) }}</p>
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
            <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Schedule</p>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ scheduleLabel(m) }}</p>
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
            <button (click)="openMicrosoftInvite()" class="btn-ghost text-xs" aria-label="Sync Microsoft Teams invite">Sync Invite</button>
          </div>
        }

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div class="lg:col-span-2 space-y-8">
            <div class="card p-6">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Default Agenda</h3>
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
              <div class="flex items-center justify-between gap-4 mb-6">
                <div>
                  <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Sessions</h3>
                  <p class="text-xs text-[var(--t-text-secondary)]">Last 3 and next 3 around {{ sessionAnchorDate }}</p>
                </div>
                <div class="flex gap-2">
                  <button type="button" (click)="pageSessions('previous')" class="btn-ghost text-xs" aria-label="Previous session window">Previous</button>
                  <button type="button" (click)="pageSessions('next')" class="btn-ghost text-xs" aria-label="Next session window">Next</button>
                </div>
              </div>
              <div class="space-y-4">
                @for (s of sessionsForDisplay(m); track s.id) {
                  <div [routerLink]="['/meetings/sessions', s.id]" class="flex items-center justify-between p-4 border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-all cursor-pointer">
                    <div class="flex items-center gap-4">
                      <div class="text-center">
                        <p class="text-xs font-black text-[var(--t-text-primary)]">{{ s.session_date | date:'dd' }}</p>
                        <p class="text-[9px] font-bold uppercase text-[var(--t-text-tertiary)]">{{ s.session_date | date:'MMM' }}</p>
                      </div>
                      <div class="w-px h-8 bg-[var(--t-border)] mx-2"></div>
                      <div>
                        <p class="text-sm font-bold text-[var(--t-text-primary)]">Review Session</p>
                        <div class="flex items-center gap-2 mt-1">
                          <span class="text-[9px] px-1.5 py-0.5 bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)] font-bold uppercase">
                            {{ scheduleLabel(m) }}
                          </span>
                          @if (s.has_transcript) {
                            <span class="text-[9px] px-1.5 py-0.5 bg-blue-500/10 text-blue-500 font-bold uppercase">Transcript</span>
                          }
                          @if (s.ai_optimised) {
                            <span class="text-[9px] px-1.5 py-0.5 bg-[var(--t-accent-soft)] text-[var(--t-accent)] font-bold uppercase">AI Optimized</span>
                          }
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <button type="button" (click)="openMicrosoftInvite(s); $event.stopPropagation()" class="btn-ghost text-[10px]" aria-label="Create Teams invite for session">Teams</button>
                      <span class="badge badge-green text-[10px]">{{ s.status | uppercase }}</span>
                    </div>
                  </div>
                }
                @if (sessionsForDisplay(m).length === 0) {
                  <div class="p-5 border border-dashed border-[var(--t-border)] text-sm text-[var(--t-text-secondary)]">
                    No sessions are scheduled in this window.
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
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 md:p-6">
          <form
            (ngSubmit)="saveMeeting()"
            class="card flex max-h-[calc(100vh-2rem)] w-full max-w-3xl flex-col overflow-hidden shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-meeting-series-title"
            style="background:var(--t-surface)">
            <div class="flex items-start justify-between gap-4 border-b border-[var(--t-border)] p-6">
              <div>
                <h2 id="edit-meeting-series-title" class="text-xl font-bold text-[var(--t-text-primary)]">Edit meeting series</h2>
                <p class="text-sm text-[var(--t-text-secondary)] mt-1">Changes save to the real meetings API.</p>
              </div>
              <button type="button" (click)="editing.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close edit meeting dialog">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <div class="min-h-0 flex-1 space-y-5 overflow-y-auto p-6">
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
                  </select>
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Recurrence</span>
                  <select [(ngModel)]="editDraft.recurrence" name="edit_recurrence" class="input-field w-full" aria-label="Meeting recurrence">
                    <option value="ad_hoc">One-off</option>
                    <option value="weekly">Weekly</option>
                    <option value="biweekly">Biweekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </label>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                @if (editDraft.recurrence === 'ad_hoc') {
                  <label>
                    <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Date</span>
                    <input [(ngModel)]="editDraft.one_off_date" name="edit_one_off_date" type="date" class="input-field w-full" aria-label="One-off date" />
                  </label>
                } @else {
                  <label>
                    <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Day</span>
                    <select [(ngModel)]="editDraft.day_of_week" name="edit_day_of_week" class="input-field w-full" aria-label="Meeting day">
                      @for (day of weekdays; track day.value) {
                        <option [ngValue]="day.value">{{ day.label }}</option>
                      }
                    </select>
                  </label>
                  <label>
                    <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Series end</span>
                    <input [(ngModel)]="editDraft.series_end_date" name="edit_series_end_date" type="date" class="input-field w-full" aria-label="Meeting series end date" />
                  </label>
                }
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Start</span>
                  <input [(ngModel)]="editDraft.start_time" name="edit_start_time" type="time" class="input-field w-full" aria-label="Meeting start time" />
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Duration</span>
                  <input [(ngModel)]="editDraft.duration_minutes" name="edit_duration_minutes" type="number" min="1" max="1440" class="input-field w-full" aria-label="Meeting duration minutes" />
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Timezone</span>
                  <input [(ngModel)]="editDraft.timezone" name="edit_timezone" class="input-field w-full" aria-label="Meeting timezone" />
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
              <fieldset class="border border-[var(--t-border)] p-3">
                <legend class="px-1 text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)]">Default Participants</legend>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                  @for (u of users(); track u.id) {
                    <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-primary)]">
                      <input
                        type="checkbox"
                        [checked]="editDraft.participant_user_ids?.includes(u.id)"
                        (change)="toggleEditParticipant(u.id, $any($event.target).checked)"
                        class="h-4 w-4"
                        [attr.aria-label]="'Select default participant ' + (u.display_name || u.email)"
                      />
                      <span class="min-w-0 truncate">{{ u.display_name || u.email }}</span>
                    </label>
                  }
                </div>
              </fieldset>
            </div>
            <div class="flex justify-end gap-3 border-t border-[var(--t-border)] p-6">
              <button type="button" (click)="editing.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" class="btn-primary text-sm">Save changes</button>
            </div>
          </form>
        </div>
      }

      @if (showMicrosoftInvite()) {
        <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
          <form (ngSubmit)="createMicrosoftEvent()" class="card w-full max-w-2xl p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Microsoft Teams invite</h2>
                <p class="text-sm text-[var(--t-text-secondary)] mt-1">Schedule the Teams meeting and send attendee invitations through Microsoft 365.</p>
              </div>
              <button type="button" (click)="showMicrosoftInvite.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close Microsoft Teams invite dialog">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Date</span>
                <input [(ngModel)]="microsoftInviteDraft.date" name="teams_date" type="date" required class="input-field w-full" aria-label="Teams invite date" />
              </label>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Start</span>
                <input [(ngModel)]="microsoftInviteDraft.start_time" name="teams_start_time" type="time" required class="input-field w-full" aria-label="Teams invite start time" />
              </label>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">End</span>
                <input [(ngModel)]="microsoftInviteDraft.end_time" name="teams_end_time" type="time" required class="input-field w-full" aria-label="Teams invite end time" />
              </label>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Timezone</span>
                <input [(ngModel)]="microsoftInviteDraft.time_zone" name="teams_time_zone" required class="input-field w-full" aria-label="Teams invite timezone" />
              </label>
              @if (!selectedTeamsSession && meeting()?.recurrence !== 'ad_hoc') {
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Series end</span>
                  <input [(ngModel)]="microsoftInviteDraft.series_end_date" name="teams_series_end_date" type="date" required class="input-field w-full" aria-label="Teams invite series end date" />
                </label>
              }
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Organizer</span>
                <select [(ngModel)]="microsoftInviteDraft.organizer_email" name="teams_organizer" class="input-field w-full" aria-label="Teams invite organizer">
                  <option value="">Default connected organizer</option>
                  @for (connection of microsoftConnections(); track connection.id) {
                    <option [value]="connection.organizer_email">{{ connection.organizer_email }}</option>
                  }
                </select>
              </label>
            </div>

            @if (!microsoftConnections().length) {
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <p class="text-sm text-[var(--t-text-secondary)]">No Microsoft organizer is connected for this tenant.</p>
                <button type="button" (click)="connectMicrosoft()" class="btn-secondary text-xs" aria-label="Connect Microsoft 365">Connect Microsoft</button>
              </div>
            }

            <fieldset class="border border-[var(--t-border)] p-4">
              <legend class="px-1 text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)]">Attendees</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                @for (attendee of (meeting()?.attendees || []); track attendee.id) {
                  <label class="flex items-center gap-3 text-sm font-bold text-[var(--t-text-primary)]">
                    <input
                      type="checkbox"
                      [checked]="microsoftInviteDraft.attendee_user_ids.includes(attendee.user_id)"
                      (change)="toggleMicrosoftInviteAttendee(attendee.user_id, $any($event.target).checked)"
                      class="h-4 w-4"
                      [attr.aria-label]="'Invite ' + (attendee.users?.display_name || attendee.users?.email || 'attendee')"
                    />
                    <span class="min-w-0 truncate">{{ attendee.users?.display_name || attendee.users?.email || attendee.user_id }}</span>
                  </label>
                }
              </div>
              @if ((meeting()?.attendees || []).length === 0) {
                <p class="mt-2 text-sm text-[var(--t-text-secondary)]">Add meeting attendees before sending Microsoft invitations.</p>
              }
            </fieldset>

            @if (microsoftInviteError()) {
              <p class="text-sm text-red-500">{{ microsoftInviteError() }}</p>
            }

            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="showMicrosoftInvite.set(false)" class="btn-ghost text-sm">Cancel</button>
              <button type="submit" [disabled]="syncingMicrosoftInvite()" class="btn-primary text-sm">
                {{ syncingMicrosoftInvite() ? 'Syncing...' : 'Create Teams Invite' }}
              </button>
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
  meetingIntegrations = signal<any[]>([]);
  agendaSuggestions = signal<any[]>([]);
  editing = signal(false);
  startingSession = signal(false);
  showMicrosoftInvite = signal(false);
  savingSuggestions = signal(false);
  syncingMicrosoftInvite = signal(false);
  suggestionsError = signal<string | null>(null);
  startSessionError = signal<string | null>(null);
  microsoftInviteError = signal<string | null>(null);
  showAgendaForm = signal(false);
  showAttendeeForm = signal(false);
  showInitiativeForm = signal(false);
  selectedUserId = '';
  selectedInitiativeId = '';
  startSessionDate = this.todayLocal();
  sessionAnchorDate = this.todayLocal();
  agendaDraft = { text: '', initiative_id: '' };
  editDraft: any = {};
  selectedTeamsSession: any | null = null;
  microsoftInviteDraft = {
    date: this.todayLocal(),
    start_time: '09:00',
    end_time: '10:00',
    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    series_end_date: '',
    organizer_email: '',
    attendee_user_ids: [] as string[],
  };
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
    this.loadMeetingIntegrations();
  }

  loadMeeting() {
    this.api.get<any>(`/meetings/${this.meetingId}`).subscribe(m => {
      this.sessionAnchorDate = m.sessions_window?.anchor_date || this.todayLocal();
      this.meeting.set(m);
    });
  }

  loadMeetingIntegrations() {
    this.api.get<any>('/meeting-integrations').subscribe({
      next: res => this.meetingIntegrations.set(res.items || []),
      error: () => this.meetingIntegrations.set([]),
    });
  }

  openEdit(meeting: any) {
    this.editDraft = {
      name: meeting.name || '',
      scope: meeting.scope || 'all',
      recurrence: meeting.recurrence || 'weekly',
      day_of_week: meeting.day_of_week ?? 0,
      one_off_date: meeting.one_off_date || this.todayLocal(),
      series_end_date: meeting.series_end_date || '',
      start_time: String(meeting.start_time || '09:00').slice(0, 5),
      timezone: meeting.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      duration_minutes: meeting.duration_minutes || 60,
      description: meeting.description || '',
      workstream_ids: (Array.isArray(meeting.workstreams) ? meeting.workstreams : [])
        .map((ws: any) => ws.id)
        .filter(Boolean),
      participant_user_ids: (Array.isArray(meeting.attendees) ? meeting.attendees : [])
        .map((attendee: any) => attendee.user_id)
        .filter(Boolean),
    };
    this.editing.set(true);
  }

  saveMeeting() {
    const payload = {
      ...this.editDraft,
      workstream_id: this.editDraft.workstream_ids?.[0] || null,
      one_off_date: this.editDraft.recurrence === 'ad_hoc' ? this.editDraft.one_off_date || null : null,
      series_end_date: this.editDraft.recurrence === 'ad_hoc' ? null : this.editDraft.series_end_date || null,
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
    this.startSessionDate = this.nextScheduledSessionDate(m) || this.todayLocal();
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

  openMicrosoftInvite(session: any | null = null) {
    const m = this.meeting();
    if (!m) return;
    this.selectedTeamsSession = session;
    const attendees = Array.isArray(session?.attendees) && session.attendees.length
      ? session.attendees
      : (Array.isArray(m.attendees) ? m.attendees : []);
    const date = session?.session_date || this.nextScheduledSessionDate(m) || this.todayLocal();
    const endTime = this.endTime(m.start_time || '09:00', Number(m.duration_minutes || 60));
    this.microsoftInviteDraft = {
      ...this.microsoftInviteDraft,
      date,
      start_time: String(m.start_time || '09:00').slice(0, 5),
      end_time: endTime,
      time_zone: m.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      series_end_date: !session && m.recurrence !== 'ad_hoc' ? m.series_end_date || this.defaultSeriesEndDate() : '',
      attendee_user_ids: attendees.map((attendee: any) => attendee.user_id).filter(Boolean),
      organizer_email: this.microsoftConnections()[0]?.organizer_email || '',
    };
    this.microsoftInviteError.set(null);
    this.showMicrosoftInvite.set(true);
  }

  createMicrosoftEvent() {
    const m = this.meeting();
    if (!m) return;
    if (!this.microsoftInviteDraft.date || !this.microsoftInviteDraft.start_time || !this.microsoftInviteDraft.end_time) {
      this.microsoftInviteError.set('Choose a date, start time, and end time.');
      return;
    }
    if (!this.selectedTeamsSession && m.recurrence !== 'ad_hoc' && !this.microsoftInviteDraft.series_end_date) {
      this.microsoftInviteError.set('Choose a series end date before creating a recurring Teams invite.');
      return;
    }
    this.syncingMicrosoftInvite.set(true);
    this.microsoftInviteError.set(null);
    const path = this.selectedTeamsSession?.id
      ? `/meetings/sessions/${this.selectedTeamsSession.id}/external-events/microsoft`
      : `/meetings/${m.id}/external-events/microsoft`;
    this.api.post<any>(path, {
      organizer_email: this.microsoftInviteDraft.organizer_email || null,
      start_date_time: `${this.microsoftInviteDraft.date}T${this.microsoftInviteDraft.start_time}:00`,
      end_date_time: `${this.microsoftInviteDraft.date}T${this.microsoftInviteDraft.end_time}:00`,
      time_zone: this.microsoftInviteDraft.time_zone || 'UTC',
      attendee_user_ids: this.microsoftInviteDraft.attendee_user_ids,
      series_end_date: !this.selectedTeamsSession && m.recurrence !== 'ad_hoc'
        ? this.microsoftInviteDraft.series_end_date || null
        : null,
    }).subscribe({
      next: event => {
        this.syncingMicrosoftInvite.set(false);
        if (event.sync_status === 'synced') {
          this.showMicrosoftInvite.set(false);
        } else {
          this.microsoftInviteError.set(event.sync_error || 'Microsoft Teams invite is not synced yet.');
        }
        this.loadMeeting();
      },
      error: err => {
        this.syncingMicrosoftInvite.set(false);
        this.microsoftInviteError.set(err.error?.detail || 'Could not create Microsoft Teams invite.');
      },
    });
  }

  connectMicrosoft() {
    this.api.post<any>('/meeting-integrations/microsoft/oauth/start', {}).subscribe({
      next: res => {
        if (res.authorization_url) {
          window.location.href = res.authorization_url;
          return;
        }
        this.microsoftInviteError.set(res.detail || 'Microsoft OAuth is not configured.');
      },
      error: err => this.microsoftInviteError.set(err.error?.detail || 'Could not start Microsoft OAuth.'),
    });
  }

  microsoftConnections(): any[] {
    return this.meetingIntegrations().filter(item =>
      item.provider === 'microsoft_graph' && item.sync_status === 'connected'
    );
  }

  toggleMicrosoftInviteAttendee(userId: string, checked: boolean): void {
    const ids = new Set<string>(this.microsoftInviteDraft.attendee_user_ids || []);
    if (checked) ids.add(userId);
    else ids.delete(userId);
    this.microsoftInviteDraft.attendee_user_ids = Array.from(ids);
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

  toggleEditParticipant(userId: string, checked: boolean): void {
    const ids = new Set<string>(this.editDraft.participant_user_ids || []);
    if (checked) ids.add(userId);
    else ids.delete(userId);
    this.editDraft.participant_user_ids = Array.from(ids);
  }

  meetingWorkstreamLabel(meeting: any): string {
    const workstreams = Array.isArray(meeting.workstreams) ? meeting.workstreams : [];
    if (!workstreams.length) return 'All';
    return workstreams.map((ws: any) => ws.name || 'Workstream').join(', ');
  }

  sessionsForDisplay(meeting: any): any[] {
    return meeting?.sessions_window?.items || meeting?.sessions || [];
  }

  pageSessions(direction: 'previous' | 'next'): void {
    const m = this.meeting();
    if (!m) return;
    const anchor = direction === 'previous'
      ? m.sessions_window?.previous_anchor_date
      : m.sessions_window?.next_anchor_date;
    if (!anchor) return;
    this.sessionAnchorDate = anchor;
    this.api.get<any>(`/meetings/${this.meetingId}/sessions`, {
      anchor_date: anchor,
      page_size: 3,
    }).subscribe(window => {
      this.meeting.set({ ...this.meeting(), sessions: window.items || [], sessions_window: window });
    });
  }

  recurrenceLabel(value: string): string {
    const labels: Record<string, string> = {
      ad_hoc: 'One-off',
      weekly: 'Weekly',
      biweekly: 'Biweekly',
      monthly: 'Monthly',
    };
    return labels[value] || value;
  }

  scheduleLabel(meeting: any): string {
    const time = String(meeting.start_time || '09:00').slice(0, 5);
    const timezone = meeting.timezone || 'UTC';
    if (meeting.recurrence === 'ad_hoc') {
      return `${meeting.one_off_date || 'One-off'} · ${time} ${timezone}`;
    }
    const day = this.weekdays.find(item => item.value === Number(meeting.day_of_week))?.short || 'Day';
    return `${day} · ${time} ${timezone}`;
  }

  nextScheduledSessionDate(meeting: any): string {
    const sessions = this.sessionsForDisplay(meeting);
    const today = this.todayLocal();
    return sessions.find(item => item.session_date >= today)?.session_date
      || sessions[sessions.length - 1]?.session_date
      || '';
  }

  endTime(start: string, durationMinutes: number): string {
    const [hours, minutes] = String(start || '09:00').slice(0, 5).split(':').map(Number);
    const date = new Date(2000, 0, 1, hours || 0, minutes || 0);
    date.setMinutes(date.getMinutes() + (durationMinutes || 60));
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  readonly weekdays = [
    { value: 0, label: 'Monday', short: 'Mon' },
    { value: 1, label: 'Tuesday', short: 'Tue' },
    { value: 2, label: 'Wednesday', short: 'Wed' },
    { value: 3, label: 'Thursday', short: 'Thu' },
    { value: 4, label: 'Friday', short: 'Fri' },
    { value: 5, label: 'Saturday', short: 'Sat' },
    { value: 6, label: 'Sunday', short: 'Sun' },
  ];

  private todayLocal(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }

  private defaultSeriesEndDate(): string {
    const now = new Date();
    now.setMonth(now.getMonth() + 3);
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }
}
