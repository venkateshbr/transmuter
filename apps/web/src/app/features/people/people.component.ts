import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-people',
  standalone: true,
  imports: [CommonModule, FormsModule],
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
          <button (click)="showInvite.set(true)" class="btn-primary text-sm flex items-center gap-2 h-10">
            <span>+</span> Invite Member
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
            Pending Invites
          </button>
        </nav>
      </div>

      <!-- Directory View -->
      @if (activeTab === 'directory') {
        <div class="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--t-border)] bg-[var(--t-surface)] p-4" data-testid="people-filters">
          <div class="relative">
            <span class="material-icons absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--t-text-tertiary)]">search</span>
            <input
              [(ngModel)]="search"
              (ngModelChange)="loadPeople()"
              class="input-field h-10 w-64 pl-9 text-sm"
              placeholder="Search people"
              aria-label="Search people"
            />
          </div>
          <select [(ngModel)]="roleFilter" (ngModelChange)="loadPeople()" class="input-field h-10 w-48 text-sm" aria-label="Filter people by role">
            <option value="">All roles</option>
            <option value="transformation_office">Transformation Office</option>
            <option value="initiative_owner">Initiative Owner</option>
            <option value="workstream_lead">Workstream Lead</option>
          </select>
          <select [(ngModel)]="statusFilter" (ngModelChange)="loadPeople()" class="input-field h-10 w-40 text-sm" aria-label="Filter people by status">
            <option value="active">Active</option>
            <option value="ghost">Ghost</option>
            <option value="deactivated">Deactivated</option>
            <option value="">All status</option>
          </select>
        </div>

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

      <!-- Pending Invites View -->
      @if (activeTab === 'pending') {
        <div class="card p-0 overflow-hidden">
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
                     <button (click)="deactivate(invite)" class="text-[9px] font-black text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] uppercase underline">Deactivate</button>
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
      }

      @if (showInvite()) {
        <div class="overlay flex items-center justify-center p-6">
          <div class="card w-full max-w-lg p-8 bg-[var(--t-surface)]">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-black text-[var(--t-text-primary)]">Invite Platform User</h2>
              <button (click)="showInvite.set(false)" class="w-9 h-9 rounded-full hover:bg-[var(--t-surface-raised)]">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <div class="space-y-4">
              <input [(ngModel)]="inviteForm.email" class="input-field w-full" placeholder="email@company.com" aria-label="Invite email" />
              <input [(ngModel)]="inviteForm.display_name" class="input-field w-full" placeholder="Display name" aria-label="Invite display name" />
              <input [(ngModel)]="inviteForm.title" class="input-field w-full" placeholder="Title" aria-label="Invite title" />
              <select [(ngModel)]="inviteForm.role" class="input-field w-full" aria-label="Invite role">
                <option value="initiative_owner">Initiative Owner</option>
                <option value="workstream_lead">Workstream Lead</option>
                <option value="transformation_office">Transformation Office</option>
              </select>
              <button (click)="createInvite()" class="btn-primary w-full h-11 rounded-xl">Send Invite</button>
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
               <button (click)="selectedUser.set(null)" class="w-10 h-10 rounded-full hover:bg-[var(--t-surface-raised)] flex items-center justify-center transition-colors">
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
                   <input [(ngModel)]="selectedUser.department" class="input-field text-sm" aria-label="User department" placeholder="Department" />
                   <input [(ngModel)]="selectedUser.market" class="input-field text-sm" aria-label="User market" placeholder="Market" />
                 </div>
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
  people = signal<any[]>([]);
  invites = signal<any[]>([]);
  
  activeTab: 'directory' | 'pending' = 'directory';
  selectedUser = signal<any | null>(null);
  showInvite = signal(false);
  search = '';
  roleFilter = '';
  statusFilter = 'active';
  inviteForm = {
    email: '',
    display_name: '',
    title: '',
    role: 'initiative_owner',
  };

  ngOnInit() {
    this.loadPeople();
    this.loadInvites();
  }

  loadPeople() {
    this.api.get<any>('/people', {
      status: this.statusFilter,
      role: this.roleFilter,
      search: this.search.trim(),
    }).subscribe(res => {
      this.people.set(res.items || []);
    });
  }

  loadInvites() {
    this.api.get<any>('/invites').subscribe(res => {
      this.invites.set(res.items || []);
    });
  }

  openProfile(user: any) {
    this.api.get<any>(`/users/${user.id}`).subscribe(profile => {
      this.selectedUser.set(profile);
    });
  }

  createInvite() {
    this.api.post<any>('/invites', this.inviteForm).subscribe(invite => {
      this.showInvite.set(false);
      this.inviteForm = { email: '', display_name: '', title: '', role: 'initiative_owner' };
      this.loadPeople();
      this.loadInvites();
      this.openProfile(invite);
    });
  }

  makeGhost(user: any) {
    this.api.post<any>(`/users/${user.id}/ghost`, {}).subscribe(updated => {
      this.selectedUser.set(updated);
      this.loadPeople();
      this.loadInvites();
    });
  }

  saveSelectedUser() {
    const user = this.selectedUser();
    if (!user) return;
    this.api.put<any>(`/users/${user.id}`, {
      display_name: user.display_name,
      title: user.title,
      department: user.department,
      market: user.market,
    }).subscribe(updated => {
      this.selectedUser.set(updated);
      this.loadPeople();
    });
  }

  deactivate(user: any) {
    this.api.post<any>(`/users/${user.id}/deactivate`, {}).subscribe(() => {
      this.selectedUser.set(null);
      this.loadPeople();
      this.loadInvites();
    });
  }

  formatRole(role: string | undefined): string {
    return (role || 'unassigned').replace(/_/g, ' ');
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
