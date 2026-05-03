import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { MilestonesTabComponent } from './milestones/milestones-tab.component';
import { KpisTabComponent } from './kpis/kpis-tab.component';
import { RisksTabComponent } from './risks/risks-tab.component';
import { StatusUpdatesTabComponent } from './status-updates/status-updates-tab.component';
import { GovernanceTabComponent } from './governance/governance-tab.component';
import { OverviewTabComponent } from './overview/overview-tab.component';
import { FinancialsTabComponent } from './financials/financials-tab.component';
import { TeamTabComponent } from './team/team-tab.component';
import { SummaryTabComponent } from './summary/summary-tab.component';

@Component({
  selector: 'app-initiative-detail',
  standalone: true,
  imports: [CommonModule, MilestonesTabComponent, KpisTabComponent, RisksTabComponent, StatusUpdatesTabComponent, GovernanceTabComponent, OverviewTabComponent, FinancialsTabComponent, TeamTabComponent, SummaryTabComponent],
  template: `
    <div class="p-8 max-w-7xl mx-auto space-y-6">
      <div class="flex items-center gap-4 mb-4">
        <a href="/initiatives/pipeline" class="text-[var(--t-text-secondary)] hover:text-[var(--t-primary)] flex items-center gap-2 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Back to Pipeline
        </a>
      </div>

      <div class="flex justify-between items-start gap-4">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            {{ initiative()?.name || 'Initiative Details' }}
          </h1>
        </div>
        <button
          type="button"
          class="btn-secondary inline-flex items-center gap-2"
          data-testid="initiative-export-workbook"
          aria-label="Export initiative workbook"
          (click)="exportWorkbook()"
          [disabled]="exporting()"
        >
          <span class="material-icons text-base">download</span>
          {{ exporting() ? 'Exporting...' : 'Export Excel' }}
        </button>
      </div>

      <div class="border-b border-[var(--t-border)]">
        <nav class="-mb-px flex space-x-8">
          <button *ngFor="let tab of tabs"
            (click)="activeTab = tab.id"
            [class.border-[var(--t-primary)]]="activeTab === tab.id"
            [class.text-[var(--t-primary)]]="activeTab === tab.id"
            [class.border-transparent]="activeTab !== tab.id"
            [class.text-[var(--t-text-secondary)]]="activeTab !== tab.id"
            class="whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-all hover:text-[var(--t-primary)]">
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <div class="mt-6">
        <app-overview-tab *ngIf="activeTab === 'overview'" [initiativeId]="id"></app-overview-tab>
        <app-financials-tab *ngIf="activeTab === 'financials'" [initiativeId]="id"></app-financials-tab>
        <app-milestones-tab *ngIf="activeTab === 'milestones'" [initiativeId]="id"></app-milestones-tab>
        <app-kpis-tab *ngIf="activeTab === 'kpis'" [initiativeId]="id"></app-kpis-tab>
        <app-risks-tab *ngIf="activeTab === 'risks'" [initiativeId]="id"></app-risks-tab>
        <app-status-updates-tab *ngIf="activeTab === 'status-updates'" [initiativeId]="id"></app-status-updates-tab>
        <app-governance-tab *ngIf="activeTab === 'governance'" [initiativeId]="id"></app-governance-tab>
        <app-team-tab *ngIf="activeTab === 'team'" [initiativeId]="id"></app-team-tab>
        <app-summary-tab *ngIf="activeTab === 'summary'" [initiativeId]="id"></app-summary-tab>
      </div>
    </div>
  `,
})
export class InitiativeDetailComponent implements OnInit {
  @Input() id!: string; // Bound from the route via withComponentInputBinding()
  
  private readonly api = inject(ApiService);
  initiative = signal<any | null>(null);
  exporting = signal(false);

  activeTab = 'overview';
  
  ngOnInit(): void {
    if (this.id) {
      this.api.get(`/initiatives/${this.id}`).subscribe({
        next: (res: any) => this.initiative.set(res),
        error: () => console.error('Failed to load initiative details')
      });
    }
  }
  
  tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'financials', label: 'Financials' },
    { id: 'milestones', label: 'Milestones' },
    { id: 'kpis', label: 'KPIs' },
    { id: 'risks', label: 'Risks' },
    { id: 'status-updates', label: 'Status' },
    { id: 'governance', label: 'Governance' },
    { id: 'team', label: 'Team' },
    { id: 'summary', label: 'Summary' }
  ];

  exportWorkbook(): void {
    if (!this.id || this.exporting()) return;
    this.exporting.set(true);
    this.api.getBlob(`/initiatives/${this.id}/export`).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `initiative-${this.id}-transmuter.xlsx`;
        link.click();
        URL.revokeObjectURL(url);
        this.exporting.set(false);
      },
      error: () => {
        this.exporting.set(false);
        alert('Failed to export initiative workbook.');
      },
    });
  }
}
