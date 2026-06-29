import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { CompactFilterToolbarComponent, type CompactFilterGroup } from '../../shared/components/compact-filter-toolbar/compact-filter-toolbar.component';
import { OPERATING_MODEL_ROLES, operatingModelRoleLabel } from '../../core/rbac/operating-model-permissions';

const PEOPLE_FILTER_STATE_KEY = 'transmuter.filters.people.directory';

@Component({
  selector: 'app-people',
  standalone: true,
  imports: [CommonModule, FormsModule, CompactFilterToolbarComponent],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            People Insight<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Strategic talent mapping, workload balancing, and platform governance.</p>
        </div>
        <div class="flex gap-3">
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="material-icons text-xs">group</span>
            <span class="text-[10px] font-black uppercase tracking-widest">{{ people().length }} ACTIVE PLATFORM USERS</span>
          </div>
          <button (click)="openUserModal()" class="btn-primary text-sm flex items-center gap-2 h-10">
            <span>+</span> Add User
          </button>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="border-b border-[var(--t-border)]">
        <nav class="-mb-px flex space-x-8">
          <button (click)="activeTab = 'directory'"
            [class.border-[var(--t-accent)]]="activeTab === 'directory'"
            [class.text-[var(--t-accent)]]="activeTab === 'directory'"
            class="whitespace-nowrap pb-4 px-1 border-b-2 font-black text-[10px] uppercase tracking-widest transition-all">
            Directory
          </button>
          <button (click)="activeTab = 'pending'"
            [class.border-[var(--t-accent)]]="activeTab === 'pending'"
            [class.text-[var(--t-accent)]]="activeTab === 'pending'"
            class="whitespace-nowrap pb-4 px-1 border-b-2 font-black text-[10px] uppercase tracking-widest transition-all">
            Pending Access
          </button>
        </nav>
      </div>

      <!-- Directory View -->
      @if (activeTab === 'directory') {
        <app-compact-filter-toolbar
          toolbarTestId="people-filters"
          [searchValue]="search"
          searchPlaceholder="Search people"
          [groups]="peopleFilterGroups()"
          [hasFilters]="hasDirectoryFilters()"
          (searchValueChange)="onSearchChange($event)"
          (groupSelectionChange)="onFilterGroupChange($event)"
          (clearFilters)="clearDirectoryFilters()" />

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          @for (p of people(); track p.id) {
            <div (click)="openProfile(p)" class="card p-6 flex flex-col items-center text-center hover:border-[var(--t-accent)] transition-all cursor-pointer group relative overflow-hidden">
              <!-- Selection Highlight -->
              <div class="absolute inset-0 bg-[var(--t-accent)] opacity-0 group-hover:opacity-[0.02] transition-opacity"></div>
              
              <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-[var(--t-surface-raised)] to-[var(--t-border)] flex items-center justify-center text-2xl font-black text-[var(--t-text-secondary)] mb-4 border border-[var(--t-border)] group-hover:scale-110 group-hover:rotate-3 transition-all duration-500">
                {{ (p.display_name || 'U').substring(0,1) }}
              </div>
              
              <h3 class="text-sm font-black text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                {{ p.display_name || 'Anonymous' }}
              </h3>
              <p class="text-[9px] font-black text-[var(--t-accent)] uppercase tracking-widest mt-1">
                {{ formatRole(p.role) }}
              </p>
              <p class="text-[10px] text-[var(--t-text-secondary)] mt-2 font-medium">{{ p.title || 'N/A' }}</p>
              <span class="mt-3 rounded bg-[var(--t-surface-raised)] px-2 py-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">
                {{ p.status }}
              </span>

              <div class="w-full mt-6 pt-6 border-t border-[var(--t-border)]/50 grid grid-cols-2 gap-4">
                <div>
                  <p class="text-[8px] font-black text-[var(--t-text-tertiary)] uppercase tracking-tighter">Initiatives</p>
                  <p class="text-lg font-black text-[var(--t-text-primary)]">{{ p.initiative_count }}</p>
                </div>
                <div>
                  <p class="text-[8px] font-black text-[var(--t-text-tertiary)] uppercase tracking-tighter">Pressure</p>
                  <p class="text-lg font-black" [style.color]="getPressureColor(p.pressure_score)">
                    {{ formatPressure(p.pressure_score) }}
                  </p>
                </div>
              </div>

              <div class="w-full mt-6 flex gap-2">
                <button (click)="openProfile(p); $event.stopPropagation()" class="flex-1 py-2 rounded-xl bg-[var(--t-surface-raised)] text-[9px] font-black uppercase tracking-widest hover:bg-[var(--t-accent-soft)] hover:text-[var(--t-accent)] transition-all">Profile</button>
                <button (click)="deactivate(p); $event.stopPropagation()" class="flex-1 py-2 rounded-xl bg-[var(--t-surface-raised)] text-[9px] font-black uppercase tracking-widest text-red-500 hover:bg-red-50 transition-all" aria-label="Deactivate user">Deactivate</button>
              </div>
            </div>
          }
        </div>
      }

      <!-- Pending Access View -->
      @if (activeTab === 'pending') {
        <div class="space-y-6">
        <div class="card p-0 overflow-hidden">
          <div class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-8 py-4">
            <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Pending Users</h2>
          </div>
          <table class="w-full text-left">
            <thead class="bg-[var(--t-surface-raised)] border-b border-[var(--t-border)]">
              <tr>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Email Identity</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Assigned Role</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] text-right">Access Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
               @for (user of pendingPeople(); track user.id) {
               <tr class="hover:bg-[var(--t-surface-raised)]/50 transition-colors">
                 <td class="px-8 py-6">
                   <p class="text-sm font-black text-[var(--t-text-primary)]">{{ user.display_name || user.email }}</p>
                   <p class="text-[10px] text-[var(--t-text-secondary)] mt-1 font-medium">{{ user.email }}</p>
                 </td>
                 <td class="px-8 py-6">
                   <span class="badge-purple font-black text-[9px] uppercase tracking-widest px-2 py-0.5">{{ formatRole(user.role) }}</span>
                 </td>
                 <td class="px-8 py-6">
                   <span class="text-xs font-black text-[var(--t-accent)]">{{ user.status | uppercase }}</span>
                 </td>
                 <td class="px-8 py-6 text-right">
                   <div class="flex justify-end gap-3">
                     <button (click)="openProfile(user)" class="text-[9px] font-black text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] uppercase underline">Profile</button>
                     <button (click)="sendPasswordSetupLink(user)" class="text-[9px] font-black text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] uppercase underline">Send Setup Link</button>
                   </div>
                 </td>
               </tr>
               } @empty {
               <tr>
                 <td colspan="4" class="px-8 py-12 text-center text-[var(--t-text-secondary)]">No pending users.</td>
               </tr>
               }
            </tbody>
          </table>
        </div>

        <div class="card p-0 overflow-hidden">
          <div class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-8 py-4">
            <h2 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Pending Invites</h2>
          </div>
          <table class="w-full text-left">
            <thead class="bg-[var(--t-surface-raised)] border-b border-[var(--t-border)]">
              <tr>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Email Identity</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Assigned Role</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Workstream</th>
                <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] text-right">Invitation Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
               @for (invite of invites(); track invite.id) {
               <tr class="hover:bg-[var(--t-surface-raised)]/50 transition-colors">
                 <td class="px-8 py-6">
                   <p class="text-sm font-black text-[var(--t-text-primary)]">{{ invite.email }}</p>
                   <p class="text-[10px] text-[var(--t-text-secondary)] mt-1 font-medium">Invited by Transformation Office</p>
                 </td>
                 <td class="px-8 py-6">
                   <span class="badge-purple font-black text-[9px] uppercase tracking-widest px-2 py-0.5">{{ formatRole(invite.role) }}</span>
                 </td>
                 <td class="px-8 py-6">
                   <span class="text-[10px] font-bold text-[var(--t-text-secondary)] uppercase">{{ invite.market || 'Unassigned' }}</span>
                 </td>
                 <td class="px-8 py-6 text-right">
                   <div class="flex flex-col items-end gap-1">
                     <span class="text-xs font-black text-[var(--t-accent)]">{{ invite.status | uppercase }}</span>
                     <div class="flex gap-3">
                       <button (click)="resendInvite(invite)" class="text-[9px] font-black text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] uppercase underline">Resend</button>
                       <button (click)="revokeInvite(invite)" class="text-[9px] font-black text-[var(--t-text-tertiary)] hover:text-[var(--t-red)] uppercase underline">Revoke</button>
                     </div>
                   </div>
                 </td>
               </tr>
               } @empty {
               <tr>
                 <td colspan="4" class="px-8 py-12 text-center text-[var(--t-text-secondary)]">No pending invites.</td>
               </tr>
               }
            </tbody>
          </table>
        </div>
        </div>
      }

      @if (showInvite()) {
        <div class="overlay flex items-center justify-center p-6">
          <div class="card w-full max-w-lg p-8 bg-[var(--t-surface)]">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-black text-[var(--t-text-primary)]">Add Platform User</h2>
              <button (click)="showInvite.set(false)" class="w-9 h-9 rounded-full hover:bg-[var(--t-surface-raised)]">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <div class="space-y-4">
              <div class="grid grid-cols-2 border border-[var(--t-border)]">
                <button
                  type="button"
                  (click)="inviteMode.set('invite')"
                  class="px-3 py-3 text-[10px] font-black uppercase tracking-widest"
                  [ngClass]="inviteMode() === 'invite' ? 'bg-[var(--t-primary)] text-white' : ''"
                  aria-label="Send invite mode">
                  Invite Link
                </button>
                <button
                  type="button"
                  (click)="inviteMode.set('create')"
                  class="border-l border-[var(--t-border)] px-3 py-3 text-[10px] font-black uppercase tracking-widest"
                  [ngClass]="inviteMode() === 'create' ? 'bg-[var(--t-primary)] text-white' : ''"
                  aria-label="Create user mode">
                  Temp Password
                </button>
              </div>
              <input [(ngModel)]="inviteForm.email" class="input-field w-full" placeholder="email@company.com" aria-label="Invite email" />
              <input [(ngModel)]="inviteForm.display_name" class="input-field w-full" placeholder="Display name" aria-label="Invite display name" />
              <input [(ngModel)]="inviteForm.title" class="input-field w-full" placeholder="Title" aria-label="Invite title" />
              <select [(ngModel)]="inviteForm.role" class="input-field w-full" aria-label="Invite role">
                @for (role of roleOptions; track role.id) {
                  <option [value]="role.id">{{ role.name }}</option>
                }
              </select>
              @if (inviteMode() === 'create') {
                <div class="grid grid-cols-[1fr_auto_auto] gap-2">
                  <input [type]="showTemporaryPassword() ? 'text' : 'password'" [(ngModel)]="inviteForm.temporary_password" class="input-field w-full" placeholder="Temporary password" aria-label="Temporary password" />
                  <button type="button" (click)="showTemporaryPassword.set(!showTemporaryPassword())" class="btn-secondary px-4 text-xs" aria-label="Toggle temporary password visibility">
                    <span class="material-icons text-sm">{{ showTemporaryPassword() ? 'visibility_off' : 'visibility' }}</span>
                  </button>
                  <button type="button" (click)="generateTemporaryPassword()" class="btn-secondary px-4 text-xs" aria-label="Generate temporary password">Generate</button>
                </div>
              }
              @if (workstreams().length) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                  <p class="mb-2 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Workstreams</p>
                  <div class="grid gap-2">
                    @for (ws of workstreams(); track ws.id) {
                      <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
                        <input type="checkbox" [checked]="inviteForm.workstream_ids.includes(ws.id)" (change)="toggleInviteWorkstream(ws.id)" [attr.aria-label]="'Assign ' + ws.name">
                        <span>{{ ws.name }}</span>
                      </label>
                    }
                  </div>
                </div>
              }
              @if (inviteError()) {
                <div class="border border-[var(--t-red)] bg-[var(--t-surface-raised)] p-3 text-sm font-bold text-[var(--t-red)]">
                  {{ inviteError() }}
                </div>
              }
              @if (inviteResult()?.invite_url) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Manual invite link</p>
                  <p class="mt-2 break-all text-xs font-bold text-[var(--t-text-secondary)]">{{ inviteResult().invite_url }}</p>
                </div>
              }
              <button
                (click)="inviteMode() === 'create' ? createUser() : createInvite()"
                class="btn-primary h-11 w-full"
                [disabled]="inviteSubmitting() || !canSubmitInvite()"
                [attr.aria-label]="inviteMode() === 'create' ? 'Create user' : 'Send invite'">
                {{ inviteSubmitting() ? 'Submitting...' : (inviteMode() === 'create' ? 'Create User' : 'Send Invite') }}
              </button>
            </div>
          </div>
        </div>
      }

      <!-- User Detail Modal / Overlay -->
      @if (selectedUser(); as selectedUser) {
        <div class="overlay flex items-center justify-end p-0">
          <div class="h-full w-full max-w-xl bg-[var(--t-surface)] shadow-2xl animate-slide-in-right flex flex-col">
            <div class="p-8 border-b border-[var(--t-border)] flex justify-between items-center bg-gradient-to-r from-[var(--t-surface)] to-[var(--t-surface-raised)]">
               <div class="flex items-center gap-4">
                  <div class="w-14 h-14 rounded-2xl bg-[var(--t-accent)] text-white flex items-center justify-center text-xl font-black">
                    {{ (selectedUser.display_name || 'U').substring(0,1) }}
                  </div>
                  <div>
                    <h2 class="text-xl font-black text-[var(--t-text-primary)]">{{ selectedUser.display_name }}</h2>
                    <p class="text-[10px] font-black text-[var(--t-accent)] uppercase tracking-widest">{{ formatRole(selectedUser.role) }}</p>
                  </div>
               </div>
               <button (click)="closeProfile()" class="w-10 h-10 rounded-full hover:bg-[var(--t-surface-raised)] flex items-center justify-center transition-colors" aria-label="Close user profile">
                 <span class="material-icons">close</span>
               </button>
            </div>

            <div class="flex-1 overflow-y-auto p-8 space-y-8">
               <section class="grid grid-cols-2 gap-4" data-testid="people-profile-details">
                 <div>
                   <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Status</p>
                   <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ selectedUser.status | uppercase }}</p>
                 </div>
                 <div>
                   <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Last Login</p>
                   <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ selectedUser.last_login_at ? (selectedUser.last_login_at | date:'medium') : 'Never' }}</p>
                 </div>
                 <div>
                   <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Email</p>
                   <p class="mt-1 break-all text-sm font-bold text-[var(--t-text-secondary)]">{{ selectedUser.email }}</p>
                 </div>
                 <div>
                   <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Timezone</p>
                   <p class="mt-1 text-sm font-bold text-[var(--t-text-secondary)]">{{ selectedUser.timezone || 'UTC' }}</p>
                 </div>
               </section>

               <section class="card p-5" data-testid="people-edit-profile">
                 <div class="mb-4 flex items-center justify-between gap-3">
                   <h3 class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Profile</h3>
                   <button type="button" (click)="saveSelectedUser()" class="btn-secondary text-xs" aria-label="Save user profile">Save Profile</button>
                 </div>
                 <div class="grid grid-cols-1 gap-3">
                   <input [(ngModel)]="selectedUser.display_name" class="input-field text-sm" aria-label="User display name" placeholder="Display name" />
                   <input [(ngModel)]="selectedUser.title" class="input-field text-sm" aria-label="User title" placeholder="Title" />
                   <select [(ngModel)]="selectedUser.role" class="input-field text-sm" aria-label="User platform role">
                     @for (role of roleOptions; track role.id) {
                       <option [value]="role.id">{{ role.name }}</option>
                     }
                   </select>
                   <input [(ngModel)]="selectedUser.department" class="input-field text-sm" aria-label="User department" placeholder="Department" />
                   <input [(ngModel)]="selectedUser.market" class="input-field text-sm" aria-label="User market" placeholder="Market" />
                 </div>
               </section>

               <section class="card p-5" data-testid="people-access-setup">
                 <div class="mb-4 flex items-center justify-between gap-3">
                   <h3 class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Access</h3>
                   <button type="button" (click)="sendPasswordSetupLink(selectedUser)" class="btn-secondary text-xs" aria-label="Send password setup link">Send Setup Link</button>
                 </div>
                 <div class="grid grid-cols-[1fr_auto_auto] gap-2">
                   <input [type]="showResetTemporaryPassword() ? 'text' : 'password'" [(ngModel)]="resetTemporaryPassword" class="input-field text-sm" placeholder="Temporary password" aria-label="Reset temporary password" />
                   <button type="button" (click)="showResetTemporaryPassword.set(!showResetTemporaryPassword())" class="btn-secondary px-4 text-xs" aria-label="Toggle reset temporary password visibility">
                     <span class="material-icons text-sm">{{ showResetTemporaryPassword() ? 'visibility_off' : 'visibility' }}</span>
                   </button>
                   <button type="button" (click)="generateResetTemporaryPassword()" class="btn-secondary px-4 text-xs" aria-label="Generate reset temporary password">Generate</button>
                 </div>
                 <button type="button" (click)="setTemporaryPassword(selectedUser)" class="btn-primary mt-3 h-10 w-full text-xs" aria-label="Set temporary password">Set Temporary Password</button>
                 @if (userAccessError()) {
                   <div class="mt-3 border border-[var(--t-red)] bg-[var(--t-surface-raised)] p-3 text-sm font-bold text-[var(--t-red)]">
                     {{ userAccessError() }}
                   </div>
                 }
                 @if (userAccessResult()?.invite_url) {
                   <div class="mt-3 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                     <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Manual setup link</p>
                     <p class="mt-2 break-all text-xs font-bold text-[var(--t-text-secondary)]">{{ userAccessResult().invite_url }}</p>
                   </div>
                 }
                 @if (userAccessResult() && !userAccessResult()?.invite_url) {
                   <p class="mt-3 text-xs font-bold text-[var(--t-accent)]">Access update sent.</p>
                 }
               </section>

               <section data-testid="people-workstreams">
                 <h3 class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-4">Workstreams</h3>
                 <div class="flex flex-wrap gap-2">
                   @for (ws of selectedUser.workstreams || []; track ws.id) {
                     <span class="rounded bg-[var(--t-accent-soft)] px-3 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
                       {{ ws.workstreams?.name || ws.workstream_id }}
                     </span>
                   } @empty {
                     <span class="text-xs text-[var(--t-text-secondary)]">No workstreams assigned.</span>
                   }
                 </div>
               </section>

               <section>
                 <h3 class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-4">On Their Plate</h3>
                 <div class="space-y-4">
                    @for (i of selectedUser.on_their_plate?.initiatives || []; track i.id) {
                      <div class="card p-5 border-l-4 border-[var(--t-accent)] flex justify-between items-center">
                        <div>
                          <p class="text-xs font-black text-[var(--t-text-primary)]">{{ i.name }}</p>
                          <p class="text-[10px] text-[var(--t-text-secondary)] mt-1">Initiative Owner · {{ i.planned_end || 'No due date' }}</p>
                        </div>
                        <span class="text-xs font-mono font-black text-[var(--t-accent)]">RAG: {{ i.rag_status | uppercase }}</span>
                      </div>
                    } @empty {
                      <p class="text-xs text-[var(--t-text-secondary)]">No active owned initiatives.</p>
                    }
                 </div>
               </section>

               <section>
                 <h3 class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-4">Milestones & Actions</h3>
                 <div class="grid grid-cols-2 gap-4">
                   <div class="card p-4 bg-[var(--t-surface-raised)] border-none">
                     <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Milestones</p>
                     <p class="mt-1 text-lg font-black">{{ selectedUser.on_their_plate?.milestones?.length || 0 }}</p>
                   </div>
                   <div class="card p-4 bg-[var(--t-surface-raised)] border-none">
                     <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Action Items</p>
                     <p class="mt-1 text-lg font-black">{{ selectedUser.on_their_plate?.action_items?.length || 0 }}</p>
                   </div>
                 </div>
               </section>

               <section class="grid grid-cols-2 gap-6">
                 <div class="card p-6 bg-[var(--t-surface-raised)] border-none">
                    <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-1">Pressure Score</p>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ formatPressure(selectedUser.pressure?.pressure_score || selectedUser.pressure_score) }}</p>
                 </div>
                 <div class="card p-6 bg-[var(--t-surface-raised)] border-none">
                    <p class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest mb-1">Market Assignment</p>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ selectedUser.market || 'Unassigned' }}</p>
                 </div>
               </section>
            </div>

            <div class="p-8 border-t border-[var(--t-border)] flex gap-4 bg-[var(--t-surface-raised)]/30">
               <button (click)="makeGhost(selectedUser)" class="flex-1 btn-primary py-3 rounded-xl shadow-lg">Convert to Ghost</button>
               <button (click)="deactivate(selectedUser)" class="flex-1 py-3 rounded-xl border border-[var(--t-border)] text-[10px] font-black uppercase tracking-widest hover:bg-white transition-all">Deactivate User</button>
            </div>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    :host { display: block; }
    .animate-slide-in-right {
      animation: slide-in-right 0.3s ease-out;
    }
    @keyframes slide-in-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
  `]
})
export class PeopleComponent implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly roleOptions = OPERATING_MODEL_ROLES;
  people = signal<any[]>([]);
  pendingPeople = signal<any[]>([]);
  invites = signal<any[]>([]);
  workstreams = signal<any[]>([]);
  
  activeTab: 'directory' | 'pending' = 'directory';
  selectedUser = signal<any | null>(null);
  showInvite = signal(false);
  inviteMode = signal<'invite' | 'create'>('invite');
  inviteResult = signal<any | null>(null);
  inviteError = signal<string | null>(null);
  inviteSubmitting = signal(false);
  userAccessResult = signal<any | null>(null);
  userAccessError = signal<string | null>(null);
  showTemporaryPassword = signal(false);
  showResetTemporaryPassword = signal(false);
  search = '';
  roleFilter = '';
  statusFilter = 'active';
  resetTemporaryPassword = '';
  inviteForm = {
    email: '',
    display_name: '',
    title: '',
    role: 'initiative_owner',
    temporary_password: '',
    workstream_ids: [] as string[],
  };

  ngOnInit() {
    this.restoreDirectoryFilters();
    this.loadPeople();
    this.loadPendingPeople();
    this.loadInvites();
    this.loadWorkstreams();
  }

  loadPeople() {
    this.persistDirectoryFilters();
    this.api.get<any>('/people', {
      status: this.statusFilter,
      role: this.roleFilter,
      search: this.search.trim(),
    }).subscribe(res => {
      this.people.set(res.items || []);
    });
  }

  loadPendingPeople() {
    this.api.get<any>('/people', { status: 'pending' }).subscribe(res => {
      this.pendingPeople.set(res.items || []);
    });
  }

  peopleFilterGroups(): CompactFilterGroup[] {
    return [
      {
        key: 'role',
        label: 'Role',
        mode: 'single',
        selected: this.roleFilter ? [this.roleFilter] : [],
        options: this.roleOptions.map(role => ({ id: role.id, name: role.name })),
      },
      {
        key: 'status',
        label: 'Status',
        mode: 'single',
        selected: this.statusFilter ? [this.statusFilter] : [],
        options: [
          { id: 'active', name: 'Active' },
          { id: 'pending', name: 'Pending' },
          { id: 'ghost', name: 'Ghost' },
          { id: 'deactivated', name: 'Deactivated' },
        ],
      },
    ];
  }

  onSearchChange(value: string): void {
    this.search = value;
    this.loadPeople();
  }

  onFilterGroupChange(change: { key: string; selected: string[] }): void {
    if (change.key === 'role') this.roleFilter = change.selected[0] || '';
    if (change.key === 'status') this.statusFilter = change.selected[0] || 'active';
    this.loadPeople();
  }

  clearDirectoryFilters(): void {
    this.search = '';
    this.roleFilter = '';
    this.statusFilter = 'active';
    this.loadPeople();
  }

  hasDirectoryFilters(): boolean {
    return Boolean(this.search.trim() || this.roleFilter || this.statusFilter !== 'active');
  }

  private persistDirectoryFilters(): void {
    localStorage.setItem(PEOPLE_FILTER_STATE_KEY, JSON.stringify({
      search: this.search,
      roleFilter: this.roleFilter,
      statusFilter: this.statusFilter,
    }));
  }

  private restoreDirectoryFilters(): void {
    try {
      const raw = localStorage.getItem(PEOPLE_FILTER_STATE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw) as Record<string, string>;
      this.search = typeof state['search'] === 'string' ? state['search'] : '';
      this.roleFilter = typeof state['roleFilter'] === 'string' ? state['roleFilter'] : '';
      this.statusFilter = typeof state['statusFilter'] === 'string' ? state['statusFilter'] : 'active';
    } catch {
      localStorage.removeItem(PEOPLE_FILTER_STATE_KEY);
    }
  }

  loadInvites() {
    this.api.get<any>('/invites').subscribe(res => {
      this.invites.set(res.items || []);
    });
  }

  loadWorkstreams() {
    this.api.get<any>('/workstreams').subscribe(res => {
      this.workstreams.set(res.items || []);
    });
  }

  openUserModal() {
    this.inviteMode.set('invite');
    this.inviteError.set(null);
    this.inviteResult.set(null);
    this.showInvite.set(true);
  }

  openProfile(user: any) {
    this.api.get<any>(`/users/${user.id}`).subscribe(profile => {
      this.userAccessResult.set(null);
      this.userAccessError.set(null);
      this.resetTemporaryPassword = '';
      this.selectedUser.set(profile);
    });
  }

  closeProfile() {
    this.selectedUser.set(null);
    this.userAccessResult.set(null);
    this.userAccessError.set(null);
    this.resetTemporaryPassword = '';
  }

  createInvite() {
    if (!this.validateInviteForm()) return;
    if (this.inviteSubmitting()) return;
    this.inviteError.set(null);
    this.inviteResult.set(null);
    this.inviteSubmitting.set(true);
    this.api.post<any>('/invites', {
      email: this.inviteForm.email,
      display_name: this.inviteForm.display_name,
      title: this.inviteForm.title,
      role: this.inviteForm.role,
      workstream_ids: this.inviteForm.workstream_ids,
    }).subscribe({
      next: invite => {
        this.inviteResult.set(invite);
        if (!invite.invite_url) {
          this.showInvite.set(false);
          this.resetInviteForm();
        }
        this.activeTab = 'pending';
        this.loadPeople();
        this.loadPendingPeople();
        this.loadInvites();
        this.inviteSubmitting.set(false);
      },
      error: err => {
        this.inviteSubmitting.set(false);
        this.inviteError.set(this.formatApiError(err));
      },
    });
  }

  createUser() {
    if (!this.inviteForm.temporary_password) this.generateTemporaryPassword();
    if (!this.validateInviteForm()) return;
    if (this.inviteSubmitting()) return;
    this.inviteError.set(null);
    this.inviteResult.set(null);
    this.inviteSubmitting.set(true);
    this.api.post<any>('/users', this.inviteForm).subscribe({
      next: user => {
        this.showInvite.set(false);
        this.resetInviteForm();
        this.loadPeople();
        this.loadPendingPeople();
        this.loadInvites();
        this.openProfile(user);
        this.inviteSubmitting.set(false);
      },
      error: err => {
        this.inviteSubmitting.set(false);
        this.inviteError.set(this.formatApiError(err));
      },
    });
  }

  canSubmitInvite(): boolean {
    const email = this.inviteForm.email.trim();
    const name = this.inviteForm.display_name.trim();
    if (!email || !name) return false;
    if (this.inviteMode() === 'create' && this.inviteForm.temporary_password.length < 12) {
      return false;
    }
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  private validateInviteForm(): boolean {
    if (this.canSubmitInvite()) return true;
    if (!this.inviteForm.email.trim()) {
      this.inviteError.set('Email is required.');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.inviteForm.email.trim())) {
      this.inviteError.set('Enter a valid email address.');
    } else if (!this.inviteForm.display_name.trim()) {
      this.inviteError.set('Display name is required.');
    } else {
      this.inviteError.set('Temporary password must be at least 12 characters.');
    }
    return false;
  }

  resendInvite(invite: any) {
    this.api.post<any>(`/invites/${invite.id}/resend`, {}).subscribe(updated => {
      this.inviteResult.set(updated);
      this.loadInvites();
    });
  }

  revokeInvite(invite: any) {
    this.api.post<any>(`/invites/${invite.id}/revoke`, {}).subscribe(() => {
      this.loadInvites();
    });
  }

  sendPasswordSetupLink(user: any) {
    this.userAccessError.set(null);
    this.userAccessResult.set(null);
    this.api.post<any>(`/users/${user.id}/password-reset-link`, {}).subscribe({
      next: result => {
        this.userAccessResult.set(result);
        this.activeTab = 'pending';
        this.loadPendingPeople();
        this.loadInvites();
      },
      error: err => this.userAccessError.set(this.formatApiError(err)),
    });
  }

  setTemporaryPassword(user: any) {
    if (!this.resetTemporaryPassword) this.generateResetTemporaryPassword();
    this.userAccessError.set(null);
    this.userAccessResult.set(null);
    this.api.post<any>(`/users/${user.id}/temporary-password`, {
      temporary_password: this.resetTemporaryPassword,
    }).subscribe({
      next: updated => {
        this.selectedUser.set(updated);
        this.resetTemporaryPassword = '';
        this.loadPeople();
        this.loadPendingPeople();
        this.loadInvites();
        this.userAccessResult.set({ status: 'temporary_password_set' });
      },
      error: err => this.userAccessError.set(this.formatApiError(err)),
    });
  }

  private formatApiError(err: unknown): string {
    const fallback = 'Request could not be completed.';
    if (!err || typeof err !== 'object') return fallback;
    const detail = (err as { error?: { detail?: unknown } }).error?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }

  generateTemporaryPassword() {
    this.inviteForm.temporary_password = this.newTemporaryPassword();
  }

  generateResetTemporaryPassword() {
    this.resetTemporaryPassword = this.newTemporaryPassword();
  }

  private newTemporaryPassword(): string {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    const token = Array.from(bytes, byte => byte.toString(36).padStart(2, '0')).join('').slice(0, 12);
    return `Transmuter${token}2026!`;
  }

  toggleInviteWorkstream(workstreamId: string) {
    const next = new Set(this.inviteForm.workstream_ids);
    if (next.has(workstreamId)) {
      next.delete(workstreamId);
    } else {
      next.add(workstreamId);
    }
    this.inviteForm.workstream_ids = Array.from(next);
  }

  private resetInviteForm() {
    this.inviteError.set(null);
    this.inviteResult.set(null);
    this.inviteSubmitting.set(false);
    this.inviteForm = {
      email: '',
      display_name: '',
      title: '',
      role: 'initiative_owner',
      temporary_password: '',
      workstream_ids: [],
    };
  }

  makeGhost(user: any) {
    this.api.post<any>(`/users/${user.id}/ghost`, {}).subscribe(updated => {
      this.selectedUser.set(updated);
      this.loadPeople();
      this.loadPendingPeople();
      this.loadInvites();
    });
  }

  saveSelectedUser() {
    const user = this.selectedUser();
    if (!user) return;
    this.api.put<any>(`/users/${user.id}`, {
      display_name: user.display_name,
      title: user.title,
      role: user.role,
      department: user.department,
      market: user.market,
    }).subscribe(updated => {
      this.selectedUser.set(updated);
      this.loadPeople();
      this.loadPendingPeople();
    });
  }

  deactivate(user: any) {
    this.api.post<any>(`/users/${user.id}/deactivate`, {}).subscribe(() => {
      this.closeProfile();
      this.loadPeople();
      this.loadPendingPeople();
      this.loadInvites();
    });
  }

  formatRole(role: string | undefined): string {
    return operatingModelRoleLabel(role);
  }

  formatPressure(score: string | number | undefined): string {
    return Number(score || 0).toFixed(1);
  }

  getPressureColor(score: string | number): string {
    const value = Number(score || 0);
    if (value < 3.4) return 'var(--t-green)';
    if (value < 6.7) return 'var(--t-amber)';
    return 'var(--t-red)';
  }
}
