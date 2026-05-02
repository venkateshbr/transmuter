import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Control Center<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Enterprise governance, system configuration, and audit accountability.</p>
        </div>
        <div class="flex gap-3">
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="material-icons text-xs">verified_user</span>
            <span class="text-[10px] font-black uppercase tracking-widest">SYSTEM SECURED</span>
          </div>
        </div>
      </div>

      <!-- Admin Navigation -->
      <div class="border-b border-[var(--t-border)]">
        <nav class="-mb-px flex space-x-8">
          @for (tab of ['General', 'Strategic Parameters', 'Access Control', 'Governance Engine', 'Audit Logs']; track tab) {
            <button (click)="activeTab = tab"
              [class.border-[var(--t-accent)]]="activeTab === tab"
              [class.text-[var(--t-accent)]]="activeTab === tab"
              class="whitespace-nowrap pb-4 px-1 border-b-2 font-black text-[10px] uppercase tracking-widest transition-all">
              {{ tab }}
            </button>
          }
        </nav>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Left: Main Content -->
        <div class="lg:col-span-2 space-y-8">
          
          @if (activeTab === 'General') {
            <div class="card p-8 space-y-8">
               <section>
                 <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-4">Organization Identity</h3>
                 <div class="grid grid-cols-2 gap-8">
                    <div class="space-y-1">
                      <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Legal Entity Name</p>
                      <input type="text" value="Ishirock International Group" class="input-field w-full">
                    </div>
                    <div class="space-y-1">
                      <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Primary Workspace Region</p>
                      <input type="text" value="Singapore (AWS-ap-southeast-1)" class="input-field w-full" disabled>
                    </div>
                 </div>
               </section>
            </div>
          }

          @if (activeTab === 'Strategic Parameters') {
            <div class="space-y-8">
              <!-- Workstreams CRUD -->
              <div class="card p-8">
                <div class="flex justify-between items-center mb-6">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Workstream Management</h3>
                    <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Configure primary portfolio streams</p>
                  </div>
                  <button (click)="addWorkstream()" class="btn-primary text-[10px] py-2 px-4 rounded-xl font-black uppercase">Add Workstream</button>
                </div>
                
                <div class="space-y-3">
                  @for (ws of workstreams(); track ws.id) {
                    <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4">
                        <div class="w-8 h-8 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
                          <span class="material-icons text-sm">hub</span>
                        </div>
                        <input type="text" [(ngModel)]="ws.name" (blur)="updateWorkstream(ws)" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-[200px]">
                      </div>
                      <button (click)="deleteWorkstream(ws.id)" class="text-red-500/40 hover:text-red-500 transition-colors">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }
                </div>
              </div>

              <!-- Business Units CRUD -->
              <div class="card p-8">
                <div class="flex justify-between items-center mb-6">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Business Units</h3>
                    <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Market and functional segments</p>
                  </div>
                  <button (click)="addBusinessUnit()" class="btn-primary text-[10px] py-2 px-4 rounded-xl font-black uppercase">Add Segment</button>
                </div>
                
                <div class="space-y-3">
                  @for (bu of businessUnits(); track bu.id) {
                    <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4">
                        <div class="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                          <span class="material-icons text-sm">business_center</span>
                        </div>
                        <input type="text" [(ngModel)]="bu.name" (blur)="updateBusinessUnit(bu)" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-[200px]">
                      </div>
                      <button (click)="deleteBusinessUnit(bu.id)" class="text-red-500/40 hover:text-red-500 transition-colors">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }
                </div>
              </div>
            </div>
          }

          @if (activeTab === 'Access Control') {
            <div class="card p-0 overflow-hidden">
               <table class="w-full text-left">
                 <thead class="bg-[var(--t-surface-raised)] border-b border-[var(--t-border)]">
                   <tr>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Identity</th>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">System Role</th>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Permitted Action</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-[var(--t-border)]">
                    <tr class="hover:bg-[var(--t-surface-raised)]/30 transition-colors">
                      <td class="px-8 py-6 flex items-center gap-4">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] flex items-center justify-center text-white font-black">A</div>
                        <div>
                          <p class="text-sm font-black text-[var(--t-text-primary)]">Admin Account</p>
                          <p class="text-[10px] text-[var(--t-text-tertiary)]">admin@ishirock.dev</p>
                        </div>
                      </td>
                      <td class="px-8 py-6">
                        <span class="badge-purple font-black text-[9px] uppercase tracking-widest">Platform Admin</span>
                      </td>
                      <td class="px-8 py-6 text-emerald-500 font-bold text-[10px] uppercase">UNRESTRICTED</td>
                    </tr>
                 </tbody>
               </table>
            </div>
          }

          @if (activeTab === 'Governance Engine') {
             <div class="card p-8">
                <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Automated Thresholds</h3>
                <div class="space-y-8">
                   <div class="space-y-4">
                      <div class="flex justify-between items-end">
                         <div>
                            <p class="text-xs font-black text-[var(--t-text-primary)]">RAG: Nuclear Status Trigger</p>
                            <p class="text-[10px] text-[var(--t-text-secondary)]">Mark initiative as 'Nuclear' if update latency exceeds X days.</p>
                         </div>
                         <span class="text-xs font-black text-[var(--t-accent)]">14 DAYS</span>
                      </div>
                      <div class="h-2 bg-[var(--t-border)] rounded-full overflow-hidden">
                        <div class="h-full bg-[var(--t-accent)]" style="width: 45%"></div>
                      </div>
                   </div>
                </div>
             </div>
          }
        </div>

        <!-- Right: System Info -->
        <div class="space-y-8">
          <div class="card p-8 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)] border-l-4 border-[var(--t-accent)]">
            <h3 class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)] mb-6">Deployment Insights</h3>
            <div class="space-y-6">
               <div class="flex items-center gap-4">
                  <div class="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center text-[var(--t-accent)] border border-[var(--t-border)]">
                     <span class="material-icons">storage</span>
                  </div>
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Database</p>
                    <p class="text-sm font-bold text-[var(--t-text-primary)]">PostgreSQL 15</p>
                  </div>
               </div>
            </div>
          </div>
        </div>

      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class AdminComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);

  activeTab = 'General';
  workstreams = signal<any[]>([]);
  businessUnits = signal<any[]>([]);

  ngOnInit() {
    this.loadWorkstreams();
    this.loadBusinessUnits();
  }

  loadWorkstreams() {
    this.api.get<any>('/workstreams').subscribe(res => this.workstreams.set(res.data || []));
  }

  loadBusinessUnits() {
    this.api.get<any>('/business-units').subscribe(res => this.businessUnits.set(res.data || []));
  }

  addWorkstream() {
    const name = prompt('Workstream Name:');
    if (!name) return;
    this.api.post('/workstreams', { name }).subscribe(() => this.loadWorkstreams());
  }

  updateWorkstream(ws: any) {
    this.api.put(`/workstreams/${ws.id}`, { name: ws.name }).subscribe();
  }

  deleteWorkstream(id: string) {
    if (confirm('Delete workstream? This cannot be undone.')) {
      this.api.delete(`/workstreams/${id}`).subscribe(() => this.loadWorkstreams());
    }
  }

  addBusinessUnit() {
    const name = prompt('Business Unit Name:');
    if (!name) return;
    this.api.post('/business-units', { name }).subscribe(() => this.loadBusinessUnits());
  }

  updateBusinessUnit(bu: any) {
    this.api.put(`/business-units/${bu.id}`, { name: bu.name }).subscribe();
  }

  deleteBusinessUnit(id: string) {
    if (confirm('Delete business unit?')) {
      this.api.delete(`/business-units/${id}`).subscribe(() => this.loadBusinessUnits());
    }
  }
}
