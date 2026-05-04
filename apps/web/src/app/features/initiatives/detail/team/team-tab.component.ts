import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-team-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-10 animate-fade-in">
      
      <!-- Stakeholder Roles Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Initiative Team<span class="text-[var(--t-accent)]">.</span></h2>
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">Stakeholder assignment & role management</p>
        </div>
        <button (click)="showAddModal.set(true)" class="btn-primary flex items-center gap-2">
          <span class="material-icons text-sm">person_add</span>
          Add Member
        </button>
      </div>

      <!-- Core Ownership Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Initiative Owner -->
        <div class="card p-8 border-t-4 border-[var(--t-accent)] relative group">
          <div class="flex items-center gap-6">
            <div class="w-20 h-20 rounded-full bg-gradient-to-br from-[var(--t-accent)] to-[var(--t-blue-light)] flex items-center justify-center text-3xl text-white font-black shadow-xl">
              {{ (initiative()?.owner_name || 'U').substring(0,1) }}
            </div>
            <div>
              <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-accent)] mb-1">Initiative Owner</p>
              <h3 class="text-2xl font-bold text-[var(--t-text-primary)]">{{ initiative()?.owner_name || 'Unassigned' }}</h3>
              <p class="text-sm text-[var(--t-text-secondary)] mt-1">Primary accountable lead for execution and value delivery.</p>
            </div>
          </div>
          <button (click)="openOwnerModal('owner')"
                  class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 focus:opacity-100 btn-ghost text-[10px] uppercase font-bold tracking-widest transition-opacity"
                  aria-label="Change initiative owner">
            Change
          </button>
        </div>

        <!-- Group Owner -->
        <div class="card p-8 border-t-4 border-[var(--t-primary)] relative group">
          <div class="flex items-center gap-6">
            <div class="w-20 h-20 rounded-full bg-[var(--t-surface-raised)] border-2 border-[var(--t-border)] flex items-center justify-center text-3xl text-[var(--t-text-tertiary)] font-black">
               {{ (initiative()?.group_owner_name || 'G').substring(0,1) }}
            </div>
            <div>
              <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-primary)] mb-1">Group Sponsor</p>
              <h3 class="text-2xl font-bold text-[var(--t-text-primary)]">{{ initiative()?.group_owner_name || 'Unassigned' }}</h3>
              <p class="text-sm text-[var(--t-text-secondary)] mt-1">Executive oversight and group-level steering.</p>
            </div>
          </div>
          <button (click)="openOwnerModal('group')"
                  class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 focus:opacity-100 btn-ghost text-[10px] uppercase font-bold tracking-widest transition-opacity"
                  aria-label="Assign group owner">
            Assign
          </button>
        </div>
      </div>

      <!-- Functional Team Members -->
      <div class="space-y-6">
        <div class="flex items-center gap-4">
          <h3 class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest shrink-0">Functional Contributors</h3>
          <div class="h-px w-full bg-[var(--t-border)]"></div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          @for (member of members(); track member.id) {
            <div class="card p-6 flex items-center gap-4 hover:border-[var(--t-accent)] transition-all group">
              <div class="w-12 h-12 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center text-lg font-bold text-[var(--t-text-primary)]">
                {{ (member.display_name || 'M').substring(0,1) }}
              </div>
              <div class="flex-1 min-w-0">
                <h4 class="font-bold text-[var(--t-text-primary)] truncate">{{ member.display_name }}</h4>
                <div class="flex items-center gap-2 mt-1">
                   <span class="text-[9px] font-bold uppercase tracking-tighter px-2 py-0.5 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                     {{ member.role }}
                   </span>
                </div>
              </div>
              @if (confirmDeleteId() === member.id) {
                <div class="flex gap-2">
                  <button (click)="removeMember(member.id)" class="text-[9px] font-black uppercase text-red-600 bg-red-50 px-2 py-1 rounded">Remove</button>
                  <button (click)="confirmDeleteId.set(null)" class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Cancel</button>
                </div>
              } @else {
                <button (click)="confirmDeleteId.set(member.id)"
                        class="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-red-500 hover:scale-110"
                        aria-label="Remove team member">
                  <span class="material-icons text-sm">person_remove</span>
                </button>
              }
            </div>
          }
          
          @if (members().length === 0) {
            <div class="col-span-full py-12 text-center border-2 border-dashed border-[var(--t-border)] rounded-2xl opacity-50">
               <span class="material-icons text-4xl mb-2">group_add</span>
               <p class="text-sm font-medium">No additional team members assigned.</p>
            </div>
          }
        </div>
      </div>

      <!-- Add Member Modal -->
      @if (showAddModal()) {
        <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div class="card glass-panel w-full max-w-md p-8 shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 class="text-xl font-bold mb-6">Assign New Stakeholder</h3>
            
            <div class="space-y-6">
              <div>
                <label class="block text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Select Person</label>
                <select [(ngModel)]="newMember.user_id" class="input-field w-full">
                  <option [value]="null">Choose a user...</option>
                  @for (user of users(); track user.id) {
                    <option [value]="user.id">{{ user.display_name }} ({{ user.role }})</option>
                  }
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Designated Role</label>
                <div class="grid grid-cols-2 gap-3">
                  @for (role of ['reviewer', 'agent', 'qa', 'member']; track role) {
                    <button 
                      (click)="newMember.role = role"
                      [class.ring-2]="newMember.role === role"
                      [class.ring-[var(--t-accent)]]="newMember.role === role"
                      class="py-2 rounded-xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] text-[10px] font-bold uppercase tracking-widest hover:bg-[var(--t-bg-card)] transition-all">
                      {{ role }}
                    </button>
                  }
                </div>
              </div>

              <div class="flex justify-end gap-3 mt-8 pt-6 border-t border-[var(--t-border)]">
                <button (click)="showAddModal.set(false)" class="btn-ghost">Cancel</button>
                <button (click)="addMember()" [disabled]="!newMember.user_id" class="btn-primary px-8">Assign Role</button>
              </div>
            </div>
          </div>
        </div>
      }

      <!-- Owner Assignment Modal -->
      @if (ownerModal()) {
        <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div class="card glass-panel w-full max-w-md p-8 shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 class="text-xl font-bold mb-2 text-[var(--t-text-primary)]">
              {{ ownerModal() === 'owner' ? 'Change Initiative Owner' : 'Assign Group Sponsor' }}
            </h3>
            <p class="text-xs mb-6 text-[var(--t-text-secondary)]">
              This updates the initiative ownership fields and refreshes the detail record.
            </p>

            <label class="block text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">
              Person
            </label>
            <select [(ngModel)]="selectedOwnerId" class="input-field w-full" aria-label="Select owner">
              <option value="">Unassigned</option>
              @for (user of users(); track user.id) {
                <option [value]="user.id">{{ user.display_name }} ({{ user.role }})</option>
              }
            </select>

            <div class="flex justify-end gap-3 mt-8 pt-6 border-t border-[var(--t-border)]">
              <button (click)="ownerModal.set(null)" class="btn-ghost">Cancel</button>
              <button (click)="saveOwner()" class="btn-primary px-8">Save</button>
            </div>
          </div>
        </div>
      }
    </div>
  `
})
export class TeamTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  initiative = signal<any>(null);
  members = signal<any[]>([]);
  users = signal<any[]>([]);
  showAddModal = signal(false);
  ownerModal = signal<'owner' | 'group' | null>(null);
  selectedOwnerId = '';
  confirmDeleteId = signal<string | null>(null);

  newMember = {
    user_id: null as string | null,
    role: 'member'
  };

  ngOnInit() {
    (globalThis as any).__transmuterTeam = this;
    this.fetchInitiative();
    this.fetchMembers();
    this.fetchUsers();
  }

  fetchInitiative() {
    this.api.get<any>(`/initiatives/${this.initiativeId}`).subscribe(res => {
      this.initiative.set(res);
    });
  }

  fetchMembers() {
    this.api.get<any>(`/initiatives/${this.initiativeId}/team`).subscribe(res => {
      this.members.set(res.data || []);
    });
  }

  fetchUsers() {
    this.api.get<any>('/people').subscribe(res => {
      this.users.set(res.data || []);
    });
  }

  openOwnerModal(kind: 'owner' | 'group') {
    const initiative = this.initiative();
    this.ownerModal.set(kind);
    this.selectedOwnerId = kind === 'owner'
      ? (initiative?.owner_id || '')
      : (initiative?.group_owner_id || '');
  }

  saveOwner() {
    const kind = this.ownerModal();
    if (!kind) return;
    const payload = kind === 'owner'
      ? { owner_id: this.selectedOwnerId || null }
      : { group_owner_id: this.selectedOwnerId || null };
    this.api.put(`/initiatives/${this.initiativeId}`, payload).subscribe(() => {
      this.ownerModal.set(null);
      this.fetchInitiative();
    });
  }

  addMember() {
    if (!this.newMember.user_id) return;
    this.api.post(`/initiatives/${this.initiativeId}/team`, this.newMember).subscribe(() => {
      this.showAddModal.set(false);
      this.newMember = { user_id: null, role: 'member' };
      this.fetchMembers();
    });
  }

  removeMember(memberId: string) {
    this.api.delete(`/initiatives/${this.initiativeId}/team/${memberId}`).subscribe(() => {
      this.confirmDeleteId.set(null);
      this.fetchMembers();
    });
  }
}
