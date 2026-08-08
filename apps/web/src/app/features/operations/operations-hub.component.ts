import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

interface OperationLink {
  label: string;
  description: string;
  route: string;
  icon: string;
}

interface OperationGroup {
  key: 'transformation' | 'financial' | 'governance';
  label: string;
  description: string;
  items: OperationLink[];
}

@Component({
  selector: 'app-operations-hub',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="min-h-screen space-y-8 bg-[var(--t-bg)] p-8" data-testid="operations-hub">
      <header class="executive-surface border-b-4 border-[var(--t-blue-light)] p-8">
        <p class="text-[10px] font-black uppercase tracking-[0.2em] text-white/65">Operating model</p>
        <h1 class="mt-3 text-3xl font-black text-white">{{ pageTitle }}<span class="text-[var(--t-blue-light)]">.</span></h1>
        <p class="mt-3 max-w-3xl text-sm font-semibold leading-6 text-white/70">
          {{ pageDescription }}
        </p>
      </header>

      <section class="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
        @for (group of visibleGroups; track group.key) {
          <article class="border border-[var(--t-border)] bg-[var(--t-surface)]">
            <div class="border-b border-[var(--t-border)] p-5">
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">{{ group.label }}</p>
              <p class="mt-2 text-xs font-semibold leading-5 text-[var(--t-text-secondary)]">{{ group.description }}</p>
            </div>
            <div class="divide-y divide-[var(--t-border)]">
              @for (item of group.items; track item.label) {
                <a [routerLink]="item.route" class="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 p-4 transition-colors hover:bg-[var(--t-surface-raised)]" [attr.aria-label]="'Open ' + item.label">
                  <span class="material-icons text-[var(--t-accent)]">{{ item.icon }}</span>
                  <span>
                    <span class="block text-sm font-black text-[var(--t-text-primary)]">{{ item.label }}</span>
                    <span class="mt-1 block text-[11px] leading-4 text-[var(--t-text-secondary)]">{{ item.description }}</span>
                  </span>
                  <span class="material-icons text-sm text-[var(--t-text-tertiary)]">arrow_forward</span>
                </a>
              }
            </div>
          </article>
        }
      </section>
    </main>
  `,
})
export class OperationsHubComponent {
  private readonly section = inject(ActivatedRoute).snapshot.data['section'] as OperationGroup['key'] | undefined;

  readonly groups: OperationGroup[] = [
    {
      key: 'transformation',
      label: 'Transformation Management',
      description: 'Maintain execution evidence, status, milestones, dependencies, risks, KPIs, and actions.',
      items: [
        { label: 'Initiative Pipeline', description: 'Create, prioritize, and maintain initiative master data.', route: '/initiatives/pipeline', icon: 'view_list' },
        { label: 'Progress Monitor', description: 'Review and maintain delivery progress.', route: '/progress', icon: 'bar_chart' },
        { label: 'Roadmap & Milestones', description: 'Manage milestone timing and dependency context.', route: '/progress/roadmap', icon: 'timeline' },
        { label: 'Action Items', description: 'Update owners, due dates, and completion status.', route: '/progress/action-items', icon: 'task_alt' },
        { label: 'Status Updates', description: 'Submit portfolio heartbeat evidence and nudges.', route: '/progress/status-updates', icon: 'update' },
        { label: 'Risk Register', description: 'Create and maintain initiative risks.', route: '/pmo/risks', icon: 'warning' },
        { label: 'KPI Management', description: 'Define outcome measures and record actuals.', route: '/pmo/kpis', icon: 'monitoring' },
      ],
    },
    {
      key: 'financial',
      label: 'Financial Operations',
      description: 'Maintain governed value commitments and evidence without editing records from dashboards.',
      items: [
        { label: 'Benefit Ledger', description: 'Enter or import realized benefit evidence.', route: '/financials/benefit-tracking', icon: 'trending_up' },
        { label: 'Benefits Register', description: 'Review validation state and accountable benefit owners.', route: '/financials/benefits-register', icon: 'fact_check' },
        { label: 'Bankable Plans', description: 'Review locks, versions, and governed rebaselines.', route: '/financials/bankable-plan', icon: 'account_balance' },
        { label: 'Waterline & Target Locks', description: 'Preview and lock workstream targets.', route: '/financials/waterline', icon: 'water_drop' },
        { label: 'Shared Costs', description: 'Configure pools, allocation rules, and posting runs.', route: '/shared-costs', icon: 'payments' },
      ],
    },
    {
      key: 'governance',
      label: 'Governance & Cadence',
      description: 'Operate decision forums and the approvals that move initiatives through the portfolio.',
      items: [
        { label: 'Gate Approvals', description: 'Approve or reject pending governance submissions.', route: '/pmo/governance', icon: 'gavel' },
        { label: 'Meetings', description: 'Manage agendas, sessions, decisions, and follow-up actions.', route: '/meetings', icon: 'calendar_month' },
      ],
    },
  ];

  readonly visibleGroups = this.section ? this.groups.filter(group => group.key === this.section) : this.groups;
  readonly pageTitle = this.section
    ? this.groups.find(group => group.key === this.section)?.label || 'Operations'
    : 'Operations';
  readonly pageDescription = this.section
    ? this.groups.find(group => group.key === this.section)?.description || ''
    : 'Create, validate, approve, lock, allocate, and maintain portfolio records here. Dashboards remain read-only decision surfaces.';
}
