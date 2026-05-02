import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-risks-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-semibold text-[var(--t-text-primary)]">Risk Register</h2>
        <button class="btn-primary">Add Risk</button>
      </div>

      <div *ngIf="loading()" class="text-center p-8 text-[var(--t-text-secondary)]">Loading Risks...</div>

      <div *ngIf="!loading() && risks().length === 0" class="card text-center py-12">
        <div class="text-[var(--t-text-secondary)]">No active risks found for this initiative.</div>
      </div>

      <div class="grid grid-cols-1 gap-4">
        <div *ngFor="let risk of risks()" class="card glass-panel hover-card">
          <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <span class="badge" 
                      [class.bg-red-500]="risk.rating === 'high'" 
                      [class.bg-orange-500]="risk.rating === 'medium'" 
                      [class.bg-green-500]="risk.rating === 'low'"
                      [class.text-white]="risk.rating">
                  {{ risk.rating | uppercase }}
                </span>
                <span class="text-sm font-medium text-[var(--t-text-tertiary)]">{{ risk.type | uppercase }}</span>
              </div>
              <h3 class="font-medium text-lg text-[var(--t-text-primary)]">{{ risk.title || risk.description }}</h3>
              
              <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span class="text-[var(--t-text-tertiary)] block text-xs">Impact</span>
                  <span class="font-medium text-[var(--t-text-secondary)] capitalize">{{ risk.impact || 'Unset' }}</span>
                </div>
                <div>
                  <span class="text-[var(--t-text-tertiary)] block text-xs">Likelihood</span>
                  <span class="font-medium text-[var(--t-text-secondary)] capitalize">{{ risk.likelihood || 'Unset' }}</span>
                </div>
                <div>
                  <span class="text-[var(--t-text-tertiary)] block text-xs">Owner</span>
                  <span class="font-medium text-[var(--t-text-secondary)]">{{ risk.owner_name || 'Unassigned' }}</span>
                </div>
                <div>
                  <span class="text-[var(--t-text-tertiary)] block text-xs">Status</span>
                  <span class="font-medium text-[var(--t-text-secondary)] capitalize">{{ risk.status }}</span>
                </div>
              </div>
            </div>
            
            <div class="flex sm:flex-col gap-2">
              <button class="btn-secondary text-sm">Update</button>
              <button *ngIf="risk.status === 'open'" class="btn-ghost text-sm text-[var(--t-primary)]">Close Risk</button>
            </div>
          </div>
          
          <div *ngIf="risk.mitigation" class="mt-4 p-3 bg-[var(--t-bg-card)] rounded-md border border-[var(--t-border)]">
            <h4 class="text-xs font-semibold text-[var(--t-text-tertiary)] uppercase mb-1">Mitigation Plan</h4>
            <p class="text-sm text-[var(--t-text-secondary)]">{{ risk.mitigation }}</p>
          </div>
        </div>
      </div>
    </div>
  `
})
export class RisksTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  risks = signal<any[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.fetchRisks();
  }

  fetchRisks() {
    this.loading.set(true);
    this.api.get<any>(`/initiatives/${this.initiativeId}/risks`).subscribe({
      next: (data) => {
        this.risks.set(data.items || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }
}
