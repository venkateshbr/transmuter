import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MilestonesTabComponent } from './milestones/milestones-tab.component';
import { KpisTabComponent } from './kpis/kpis-tab.component';
import { RisksTabComponent } from './risks/risks-tab.component';
import { StatusUpdatesTabComponent } from './status-updates/status-updates-tab.component';
import { GovernanceTabComponent } from './governance/governance-tab.component';
import { OverviewTabComponent } from './overview/overview-tab.component';

@Component({
  selector: 'app-initiative-detail',
  standalone: true,
  imports: [CommonModule, MilestonesTabComponent, KpisTabComponent, RisksTabComponent, StatusUpdatesTabComponent, GovernanceTabComponent, OverviewTabComponent],
  template: `
    <div class="p-8 max-w-7xl mx-auto space-y-6">
      <div class="flex items-center gap-4 mb-4">
        <a href="/initiatives/pipeline" class="text-[var(--t-text-secondary)] hover:text-[var(--t-primary)] flex items-center gap-2 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Back to Pipeline
        </a>
      </div>

      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">Initiative Details</h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Manage project milestones, KPIs, and risks.</p>
        </div>
      </div>

      <div class="border-b border-[var(--t-border)]">
        <nav class="-mb-px flex space-x-8">
          <button *ngFor="let tab of tabs"
            (click)="activeTab = tab.id"
            [class.border-[var(--t-primary)]]="activeTab === tab.id"
            [class.text-[var(--t-primary)]]="activeTab === tab.id"
            [class.border-transparent]="activeTab !== tab.id"
            [class.text-[var(--t-text-secondary)]]="activeTab !== tab.id"
            class="whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors hover:text-[var(--t-primary)]">
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <div class="mt-6">
        <app-overview-tab *ngIf="activeTab === 'overview'" [initiativeId]="id"></app-overview-tab>
        <app-milestones-tab *ngIf="activeTab === 'milestones'" [initiativeId]="id"></app-milestones-tab>
        <app-kpis-tab *ngIf="activeTab === 'kpis'" [initiativeId]="id"></app-kpis-tab>
        <app-risks-tab *ngIf="activeTab === 'risks'" [initiativeId]="id"></app-risks-tab>
        <app-status-updates-tab *ngIf="activeTab === 'status-updates'" [initiativeId]="id"></app-status-updates-tab>
        <app-governance-tab *ngIf="activeTab === 'governance'" [initiativeId]="id"></app-governance-tab>
        
        <!-- Placeholders for remaining tabs -->
        <div *ngIf="activeTab === 'financials' || activeTab === 'team'" class="card text-center py-12">
          <div class="text-[var(--t-text-secondary)]">Content for {{ activeTab }} coming soon.</div>
        </div>
      </div>
    </div>
  `,
})
export class InitiativeDetailComponent {
  @Input() id!: string; // Bound from the route via withComponentInputBinding()
  
  activeTab = 'overview';
  
  tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'milestones', label: 'Milestones' },
    { id: 'kpis', label: 'KPIs & Targets' },
    { id: 'financials', label: 'Financials' },
    { id: 'risks', label: 'Risks' },
    { id: 'status-updates', label: 'Status Updates' },
    { id: 'governance', label: 'Governance' },
    { id: 'team', label: 'Team' }
  ];
}
