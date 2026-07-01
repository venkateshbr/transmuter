import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject, forkJoin, interval, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import { TimezoneOptionsService } from '../../../core/services/timezone-options.service';

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
                <span class="badge text-[9px]" [class.badge-red]="s.status === 'in_progress'" [class.badge-gray]="s.status !== 'in_progress'">
                  {{ s.status === 'in_progress' ? 'Live' : (s.status || 'scheduled') }}
                </span>
              </div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                {{ s.session_date | date:'EEE, MMM d' }} · {{ duration() }} · {{ saveStatus() }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            @if (teamsJoinUrl()) {
              <a [href]="teamsJoinUrl()" target="_blank" rel="noreferrer" class="btn-secondary text-xs" aria-label="Join Microsoft Teams meeting">Join Teams</a>
            }
            <button class="btn-ghost text-xs" (click)="generateAgendaSuggestions()">Generate Agenda</button>
            <button class="btn-secondary text-xs" (click)="openTeamsInvite()">Teams Invite</button>
            <button class="btn-ghost text-xs" (click)="openTranscriptModal()">Import Transcript</button>
            <button class="btn-secondary text-xs" (click)="generateMinutes()">Generate Minutes</button>
            <button class="btn-ghost text-xs" [disabled]="!session()?.minutes_markdown || sendingMinutes()" (click)="sendMinutes()">
              {{ sendingMinutes() ? 'Sending...' : (session()?.minutes_status === 'sent' ? 'Sent' : 'Send Minutes') }}
            </button>
            @if (s.status === 'scheduled') {
              <button class="btn-primary text-xs px-5" (click)="startScheduledSession()">Start Session</button>
            } @else {
              <button class="btn-primary text-xs px-5" (click)="endSession()">Complete Session</button>
            }
          </div>
        </header>

        <main class="flex-1 grid grid-cols-[280px_minmax(0,1fr)_380px] overflow-hidden">
          <aside class="border-r border-[var(--t-border)] bg-[var(--t-surface-raised)]/35 overflow-y-auto">
            <div class="p-4 space-y-5">
              <section>
                <div class="flex items-center justify-between mb-3">
                  <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Agenda</h2>
                  <button class="text-[10px] font-bold text-[var(--t-accent)]" (click)="showAgendaForm.set(!showAgendaForm())" aria-label="Add session agenda item">+ Add</button>
                </div>
                @if (showAgendaForm()) {
                  <div class="mb-3 space-y-2">
                    <textarea [(ngModel)]="agendaDraft.text" rows="3" class="input-field w-full text-xs resize-none" aria-label="Session agenda item"></textarea>
                    <button class="btn-secondary w-full text-[10px]" (click)="addSessionAgendaItem()">Add Agenda Item</button>
                  </div>
                }
                <div class="space-y-2">
                  @for (item of s.agenda; track item.id; let i = $index) {
                    <div
                      class="w-full text-left p-3 border transition-colors cursor-pointer"
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
                        <button class="ml-auto text-[var(--t-text-tertiary)] hover:text-red-500" (click)="deleteSessionAgendaItem(item.id); $event.stopPropagation()" aria-label="Delete session agenda item">
                          <span class="material-icons text-sm">close</span>
                        </button>
                      </div>
                    </div>
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
                  <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Attendees</h2>
                  <button class="text-[10px] font-bold text-[var(--t-accent)]" (click)="showAttendeeForm.set(!showAttendeeForm())" aria-label="Add session attendee">+ Add</button>
                </div>
                @if (showAttendeeForm()) {
                  <div class="mb-3 flex gap-2">
                    <select [(ngModel)]="selectedUserId" class="input-field min-w-0 flex-1 text-xs" aria-label="Session attendee">
                      @for (u of users(); track u.id) {
                        <option [value]="u.id">{{ u.display_name || u.email }}</option>
                      }
                    </select>
                    <button class="btn-secondary text-[10px]" (click)="addSessionAttendee()">Add</button>
                  </div>
                }
                <div class="space-y-2">
                  @for (attendee of s.attendees || []; track attendee.id) {
                    <div class="flex items-center justify-between gap-2 p-2 bg-[var(--t-surface)] border border-[var(--t-border)]">
                      <span class="truncate text-xs font-bold text-[var(--t-text-primary)]">{{ attendee.users?.display_name || attendee.users?.email || attendee.user_id }}</span>
                      <button class="text-[var(--t-text-tertiary)] hover:text-red-500" (click)="deleteSessionAttendee(attendee.id)" aria-label="Remove session attendee">
                        <span class="material-icons text-sm">close</span>
                      </button>
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
              @if (sessionError()) {
                <div class="border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
                  {{ sessionError() }}
                </div>
              }
              @if (sessionMessage()) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3 text-sm font-bold text-[var(--t-accent)]">
                  {{ sessionMessage() }}
                </div>
              }

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

        @if (showTranscriptImport()) {
          <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
            <form (ngSubmit)="importTranscript()" class="card w-full max-w-2xl p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Import transcript</h2>
                  <p class="text-sm text-[var(--t-text-secondary)] mt-1">Paste a transcript or upload a .txt file.</p>
                </div>
                <button type="button" (click)="showTranscriptImport.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close transcript import dialog">
                  <span class="material-icons text-sm">close</span>
                </button>
              </div>
              <label>
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Transcript Text</span>
                <textarea [(ngModel)]="transcriptDraft" name="transcript_text" rows="12" class="input-field w-full resize-none text-sm" aria-label="Transcript text"></textarea>
              </label>
              <label class="block">
                <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Text File</span>
                <input type="file" accept=".txt,text/plain" (change)="onTranscriptFile($event)" class="input-field w-full text-sm" aria-label="Upload transcript text file" />
              </label>
              @if (transcriptFileName()) {
                <p class="text-xs font-bold text-[var(--t-text-secondary)]">{{ transcriptFileName() }}</p>
              }
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Microsoft Teams</p>
                  <p class="mt-1 text-sm text-[var(--t-text-secondary)]">Sync the transcript from the Teams event after transcription has finished.</p>
                </div>
                <button type="button" (click)="syncMicrosoftTranscript()" [disabled]="syncingMicrosoftTranscript()" class="btn-secondary text-xs" aria-label="Sync Microsoft Teams transcript">
                  {{ syncingMicrosoftTranscript() ? 'Syncing...' : 'Sync from Microsoft' }}
                </button>
              </div>
              <div class="flex justify-end gap-3 pt-2">
                <button type="button" (click)="showTranscriptImport.set(false)" class="btn-ghost text-sm">Cancel</button>
                <button type="submit" [disabled]="!transcriptDraft.trim() || importingTranscript()" class="btn-primary text-sm">
                  {{ importingTranscript() ? 'Importing...' : 'Import transcript' }}
                </button>
              </div>
            </form>
          </div>
        }

        @if (showTeamsInvite()) {
          <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
            <form (ngSubmit)="syncTeamsInvite()" class="card w-full max-w-2xl p-6 space-y-5 shadow-2xl" style="background:var(--t-surface)">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Session Teams invite</h2>
                  <p class="text-sm text-[var(--t-text-secondary)] mt-1">Creates or updates the Microsoft Teams event for this dated session only.</p>
                </div>
                <button type="button" (click)="showTeamsInvite.set(false)" class="btn-ghost h-9 w-9 p-0" aria-label="Close Teams invite dialog">
                  <span class="material-icons text-sm">close</span>
                </button>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Date</span>
                  <input [(ngModel)]="teamsDraft.date" name="session_teams_date" type="date" required class="input-field w-full" aria-label="Teams date" />
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Start</span>
                  <input [(ngModel)]="teamsDraft.start_time" name="session_teams_start" type="time" required class="input-field w-full" aria-label="Teams start time" />
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">End</span>
                  <input [(ngModel)]="teamsDraft.end_time" name="session_teams_end" type="time" required class="input-field w-full" aria-label="Teams end time" />
                </label>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Timezone</span>
                  <select [(ngModel)]="teamsDraft.time_zone" name="session_teams_timezone" required class="input-field w-full" aria-label="Teams timezone">
                    @for (timezone of timezoneOptions(teamsDraft.time_zone); track timezone.value) {
                      <option [value]="timezone.value">{{ timezone.label }}</option>
                    }
                  </select>
                </label>
                <label>
                  <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Organizer</span>
                  <select [(ngModel)]="teamsDraft.organizer_email" name="session_teams_organizer" class="input-field w-full" aria-label="Teams organizer">
                    <option value="">Default connected organizer</option>
                    @for (connection of microsoftConnections(); track connection.id) {
                      <option [value]="connection.organizer_email">{{ connection.organizer_email }}</option>
                    }
                  </select>
                </label>
              </div>
              @if (teamsInviteError()) {
                <p class="text-sm text-red-500">{{ teamsInviteError() }}</p>
              }
              <div class="flex justify-end gap-3 pt-2">
                <button type="button" (click)="showTeamsInvite.set(false)" class="btn-ghost text-sm">Cancel</button>
                <button type="submit" [disabled]="syncingTeamsInvite()" class="btn-primary text-sm">
                  {{ syncingTeamsInvite() ? 'Syncing...' : 'Send / Update Invite' }}
                </button>
              </div>
            </form>
          </div>
        }
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
  private readonly timezones = inject(TimezoneOptionsService);
  private readonly destroy$ = new Subject<void>();
  private readonly notesChanged$ = new Subject<string>();

  session = signal<any>(null);
  users = signal<any[]>([]);
  meetingIntegrations = signal<any[]>([]);
  artifacts = signal<MeetingArtifact[]>([]);
  initiativeContext = signal<any | null>(null);
  activeAgendaIndex = signal(0);
  duration = signal('00:00:00');
  saveStatus = signal('All changes saved');
  showTranscriptImport = signal(false);
  showAgendaForm = signal(false);
  showAttendeeForm = signal(false);
  showTeamsInvite = signal(false);
  importingTranscript = signal(false);
  syncingMicrosoftTranscript = signal(false);
  syncingTeamsInvite = signal(false);
  sendingMinutes = signal(false);
  transcriptFileName = signal('');
  sessionError = signal<string | null>(null);
  sessionMessage = signal<string | null>(null);
  teamsInviteError = signal<string | null>(null);
  notes = '';
  minutesDraft = '';
  transcriptDraft = '';
  selectedUserId = '';
  agendaDraft = { text: '' };
  teamsDraft = {
    date: '',
    start_time: '09:00',
    end_time: '10:00',
    time_zone: this.timezones.browserTimezone(),
    organizer_email: '',
  };
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

  teamsJoinUrl = computed(() => {
    const events = this.session()?.external_events || [];
    const event = events.find((item: any) => item.provider === 'microsoft' && item.join_url);
    return event?.join_url || '';
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
    this.timezones.load();
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.loadSession(id);
    this.loadUsers();
    this.loadMeetingIntegrations();

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

  loadUsers() {
    this.api.get<any>('/users').subscribe(res => {
      const users = res.data || [];
      this.users.set(users);
      this.selectedUserId = users[0]?.id || '';
    });
  }

  loadMeetingIntegrations() {
    this.api.get<any>('/meeting-integrations').subscribe({
      next: res => this.meetingIntegrations.set(res.items || []),
      error: () => this.meetingIntegrations.set([]),
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

  addSessionAgendaItem() {
    const session = this.session();
    const text = this.agendaDraft.text.trim();
    if (!session?.id || !text) return;
    this.api.post<any>(`/meetings/sessions/${session.id}/agenda`, { text }).subscribe({
      next: () => {
        this.agendaDraft = { text: '' };
        this.showAgendaForm.set(false);
        this.loadSession(session.id);
      },
      error: err => this.sessionError.set(err.error?.detail || 'Could not add agenda item.'),
    });
  }

  deleteSessionAgendaItem(itemId: string) {
    const id = this.session()?.id;
    if (!id) return;
    this.api.delete(`/meetings/sessions/${id}/agenda/${itemId}`).subscribe({
      next: () => this.loadSession(id),
      error: err => this.sessionError.set(err.error?.detail || 'Could not delete agenda item.'),
    });
  }

  generateAgendaSuggestions() {
    const id = this.session()?.id;
    if (!id) return;
    this.sessionError.set(null);
    this.api.post<any>(`/meetings/sessions/${id}/agenda/suggestions`, {}).subscribe({
      next: res => {
        const items = (res.items || [])
          .map((item: any, index: number) => ({
            text: item.text,
            initiative_id: item.initiative_id || null,
            sort_order: (this.session()?.agenda || []).length + index + 1,
          }))
          .filter((item: any) => String(item.text || '').trim());
        if (!items.length) {
          this.sessionMessage.set('No agenda suggestions were available.');
          return;
        }
        forkJoin(items.map((item: any) => this.api.post<any>(`/meetings/sessions/${id}/agenda`, item))).subscribe({
          next: () => {
            this.sessionMessage.set('Agenda suggestions added.');
            this.loadSession(id);
          },
          error: err => this.sessionError.set(err.error?.detail || 'Could not save agenda suggestions.'),
        });
      },
      error: err => this.sessionError.set(err.error?.detail || 'Could not generate agenda suggestions.'),
    });
  }

  addSessionAttendee() {
    const id = this.session()?.id;
    if (!id || !this.selectedUserId) return;
    this.api.post<any>(`/meetings/sessions/${id}/attendees`, { user_id: this.selectedUserId }).subscribe({
      next: () => {
        this.showAttendeeForm.set(false);
        this.loadSession(id);
      },
      error: err => this.sessionError.set(err.error?.detail || 'Could not add attendee.'),
    });
  }

  deleteSessionAttendee(attendeeId: string) {
    const id = this.session()?.id;
    if (!id) return;
    this.api.delete(`/meetings/sessions/${id}/attendees/${attendeeId}`).subscribe({
      next: () => this.loadSession(id),
      error: err => this.sessionError.set(err.error?.detail || 'Could not remove attendee.'),
    });
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
      agenda_item_id: active?.source_agenda_item_id || null,
      initiative_id: active?.initiative_id || null,
    };
    this.api.post<MeetingArtifact>(`/meetings/sessions/${session.id}/artifacts`, body).subscribe(item => {
      this.artifacts.set([item, ...this.artifacts()]);
      this.newActionItem = '';
      this.loadSession(session.id);
    });
  }

  updateArtifact(artifact: MeetingArtifact, patch: Record<string, string | null>) {
    this.api.put<MeetingArtifact>(`/meetings/artifacts/${artifact.id}`, patch).subscribe(updated => {
      this.artifacts.set(this.artifacts().map(item => item.id === artifact.id ? { ...item, ...updated } : item));
    });
  }

  deleteArtifact(artifact: MeetingArtifact) {
    this.api.delete(`/meetings/artifacts/${artifact.id}`).subscribe(() => {
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

  openTranscriptModal() {
    this.sessionError.set(null);
    this.sessionMessage.set(null);
    this.transcriptDraft = this.session()?.transcript_text || '';
    this.transcriptFileName.set('');
    this.showTranscriptImport.set(true);
  }

  openTeamsInvite() {
    const session = this.session();
    if (!session) return;
    const meeting = session.meetings || {};
    const start = String(meeting.start_time || '09:00').slice(0, 5);
    this.teamsDraft = {
      date: session.session_date || this.todayLocal(),
      start_time: start,
      end_time: this.endTime(start, Number(meeting.duration_minutes || 60)),
      time_zone: meeting.timezone || this.timezones.browserTimezone(),
      organizer_email: this.microsoftConnections()[0]?.organizer_email || '',
    };
    this.teamsInviteError.set(null);
    this.showTeamsInvite.set(true);
  }

  timezoneOptions(currentValue?: string | null) {
    return this.timezones.optionsWithCurrent(currentValue);
  }

  syncTeamsInvite() {
    const id = this.session()?.id;
    if (!id) return;
    this.syncingTeamsInvite.set(true);
    this.teamsInviteError.set(null);
    this.api.post<any>(`/meetings/sessions/${id}/external-events/microsoft`, {
      organizer_email: this.teamsDraft.organizer_email || null,
      start_date_time: `${this.teamsDraft.date}T${this.teamsDraft.start_time}:00`,
      end_date_time: `${this.teamsDraft.date}T${this.teamsDraft.end_time}:00`,
      time_zone: this.teamsDraft.time_zone || 'UTC',
      attendee_user_ids: (this.session()?.attendees || []).map((item: any) => item.user_id).filter(Boolean),
    }).subscribe({
      next: event => {
        this.syncingTeamsInvite.set(false);
        if (event.sync_status === 'synced') {
          this.showTeamsInvite.set(false);
          this.sessionMessage.set('Teams invite synced.');
        } else {
          this.teamsInviteError.set(event.sync_error || 'Microsoft Teams invite is not synced yet.');
        }
        this.loadSession(id);
      },
      error: err => {
        this.syncingTeamsInvite.set(false);
        this.teamsInviteError.set(err.error?.detail || 'Could not sync Teams invite.');
      },
    });
  }

  microsoftConnections(): any[] {
    return this.meetingIntegrations().filter(item =>
      item.provider === 'microsoft_graph' && item.sync_status === 'connected'
    );
  }

  onTranscriptFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.txt') && file.type !== 'text/plain') {
      this.sessionError.set('Upload a .txt transcript file.');
      input.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      this.transcriptDraft = String(reader.result || '');
      this.transcriptFileName.set(file.name);
    };
    reader.onerror = () => this.sessionError.set('Could not read transcript file.');
    reader.readAsText(file);
  }

  importTranscript() {
    const id = this.session()?.id;
    if (!id) return;
    const transcript = this.transcriptDraft.trim();
    if (!transcript) {
      this.sessionError.set('Paste transcript text or upload a .txt file before importing.');
      return;
    }
    this.importingTranscript.set(true);
    this.sessionError.set(null);
    this.api.post<any>(`/meetings/sessions/${id}/transcript/import`, {
      transcript_text: transcript,
      transcript_source: this.transcriptFileName() ? 'txt_upload' : 'manual',
    }).subscribe({
      next: s => {
        this.importingTranscript.set(false);
        this.showTranscriptImport.set(false);
        this.session.set({ ...this.session(), ...s, has_transcript: true });
        this.sessionMessage.set('Transcript imported.');
      },
      error: err => {
        this.importingTranscript.set(false);
        this.sessionError.set(err.error?.detail || 'Could not import transcript.');
      },
    });
  }

  syncMicrosoftTranscript() {
    const id = this.session()?.id;
    if (!id) return;
    this.syncingMicrosoftTranscript.set(true);
    this.sessionError.set(null);
    this.sessionMessage.set(null);
    this.api.post<any>(`/meetings/sessions/${id}/transcript/sync/microsoft`, {}).subscribe({
      next: res => {
        this.syncingMicrosoftTranscript.set(false);
        if (res.status === 'synced' && res.session) {
          this.showTranscriptImport.set(false);
          this.session.set({ ...this.session(), ...res.session, has_transcript: true });
          this.transcriptDraft = res.session.transcript_text || '';
          this.sessionMessage.set('Microsoft Teams transcript synced.');
          return;
        }
        this.sessionMessage.set(res.detail || 'Microsoft Teams transcript is not available yet.');
      },
      error: err => {
        this.syncingMicrosoftTranscript.set(false);
        this.sessionError.set(err.error?.detail || 'Could not sync Microsoft Teams transcript.');
      },
    });
  }

  generateMinutes() {
    const id = this.session()?.id;
    if (!id) return;
    this.sessionError.set(null);
    this.api.post<any>(`/meetings/sessions/${id}/minutes/generate`, { force: true }).subscribe({
      next: s => {
        this.session.set({ ...this.session(), ...s });
        this.minutesDraft = s.minutes_markdown || '';
        this.sessionMessage.set('Draft minutes generated.');
      },
      error: err => this.sessionError.set(err.error?.detail || 'Could not generate minutes.'),
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
    this.sendingMinutes.set(true);
    this.sessionError.set(null);
    this.api.patch<any>(`/meetings/sessions/${id}`, {
      minutes_markdown: this.minutesDraft,
      minutes_status: 'draft',
    }).subscribe({
      next: saved => {
        this.session.set({ ...this.session(), ...saved });
        this.api.post<any>(`/meetings/sessions/${id}/minutes/send`, {}).subscribe({
          next: sent => {
            this.sendingMinutes.set(false);
            this.session.set({ ...this.session(), ...sent });
            this.sessionMessage.set('Minutes sent.');
          },
          error: err => {
            this.sendingMinutes.set(false);
            this.sessionError.set(err.error?.detail || 'Could not send minutes.');
          },
        });
      },
      error: err => {
        this.sendingMinutes.set(false);
        this.sessionError.set(err.error?.detail || 'Could not save draft minutes.');
      },
    });
  }

  endSession() {
    const id = this.session()?.id;
    if (!id) return;
    this.api.post(`/meetings/sessions/${id}/end`, {}).subscribe(() => {
      this.router.navigate(['/meetings', this.session().meeting_id]);
    });
  }

  startScheduledSession() {
    const session = this.session();
    if (!session?.meeting_id) return;
    this.api.post<any>(`/meetings/${session.meeting_id}/sessions/start`, {
      session_date: session.session_date,
    }).subscribe({
      next: updated => {
        this.session.set({ ...this.session(), ...updated });
        this.sessionMessage.set('Session started.');
      },
      error: err => this.sessionError.set(err.error?.detail || 'Could not start session.'),
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

  endTime(start: string, durationMinutes: number): string {
    const [hours, minutes] = String(start || '09:00').slice(0, 5).split(':').map(Number);
    const date = new Date(2000, 0, 1, hours || 0, minutes || 0);
    date.setMinutes(date.getMinutes() + (durationMinutes || 60));
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  private todayLocal(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }
}
