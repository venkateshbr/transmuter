import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { MilestonesTabComponent } from './milestones/milestones-tab.component';
import { KpisTabComponent } from './kpis/kpis-tab.component';
import { RisksTabComponent } from './risks/risks-tab.component';
import { StatusUpdatesTabComponent } from './status-updates/status-updates-tab.component';
import { GovernanceTabComponent } from './governance/governance-tab.component';
import { OverviewTabComponent } from './overview/overview-tab.component';
import { FinancialsTabComponent } from './financials/financials-tab.component';
import { TeamTabComponent } from './team/team-tab.component';
import { SummaryTabComponent } from './summary/summary-tab.component';
import { DependenciesTabComponent } from './dependencies/dependencies-tab.component';

@Component({
  selector: 'app-initiative-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, MilestonesTabComponent, KpisTabComponent, RisksTabComponent, StatusUpdatesTabComponent, GovernanceTabComponent, OverviewTabComponent, FinancialsTabComponent, TeamTabComponent, SummaryTabComponent, DependenciesTabComponent],
  template: `
    <div class="p-8 max-w-7xl mx-auto space-y-6">
      <div class="flex items-center gap-4 mb-4">
        <a routerLink="/initiatives/pipeline" class="text-[var(--t-text-secondary)] hover:text-[var(--t-primary)] flex items-center gap-2 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Back to Pipeline
        </a>
      </div>

      @if (loadError()) {
        <section class="border border-[var(--t-border)] bg-[var(--t-surface)] p-8 shadow-[var(--t-shadow)]">
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Initiative unavailable</p>
          <h1 class="mt-3 text-3xl font-black text-[var(--t-text-primary)]">You cannot view this initiative</h1>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-[var(--t-text-secondary)]">
            The initiative may not exist, may belong to another tenant, or may not be assigned to your role.
          </p>
          <a routerLink="/initiatives/pipeline" class="btn-secondary mt-6 inline-flex text-xs">
            Back to pipeline
          </a>
        </section>
      } @else {
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
              {{ initiative()?.name || 'Initiative Details' }}
            </h1>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            @if (canEditInitiative()) {
              <a
                [routerLink]="['/initiatives', id, 'edit']"
                class="btn-primary inline-flex items-center gap-2"
                aria-label="Edit initiative"
                title="Edit initiative"
              >
                <span class="material-icons text-base">edit</span>
                Edit Initiative
              </a>
            }
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
          <app-dependencies-tab *ngIf="activeTab === 'dependencies'" [initiativeId]="id"></app-dependencies-tab>
          <app-status-updates-tab *ngIf="activeTab === 'status-updates'" [initiativeId]="id"></app-status-updates-tab>
          <app-governance-tab *ngIf="activeTab === 'governance'" [initiativeId]="id"></app-governance-tab>
          <app-team-tab *ngIf="activeTab === 'team'" [initiativeId]="id"></app-team-tab>
          <app-summary-tab *ngIf="activeTab === 'summary'" [initiativeId]="id"></app-summary-tab>
        </div>
      }
    </div>
  `,
})
export class InitiativeDetailComponent implements OnInit {
  @Input() id!: string; // Bound from the route via withComponentInputBinding()
  
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  initiative = signal<any | null>(null);
  loadError = signal(false);
  exporting = signal(false);

  activeTab = 'overview';
  
  ngOnInit(): void {
    if (this.id) {
      this.api.get(`/initiatives/${this.id}`).subscribe({
        next: (res: any) => {
          this.initiative.set(res);
          this.loadError.set(false);
        },
        error: () => {
          this.initiative.set(null);
          this.loadError.set(true);
        }
      });
    }
  }
  
  tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'financials', label: 'Financials' },
    { id: 'milestones', label: 'Milestones' },
    { id: 'kpis', label: 'KPIs' },
    { id: 'risks', label: 'Risks' },
    { id: 'dependencies', label: 'Dependencies' },
    { id: 'status-updates', label: 'Status' },
    { id: 'governance', label: 'Governance' },
    { id: 'team', label: 'Team' },
    { id: 'summary', label: 'Summary' }
  ];

  canEditInitiative(): boolean {
    return this.auth.hasPermission('initiatives.manage_all')
      || this.auth.hasPermission('initiatives.manage_assigned')
      || this.auth.hasPermission('initiatives.manage_workstream');
  }

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
