import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="min-h-screen bg-[var(--t-bg)] text-[var(--t-text-primary)]">
      <header class="border-b border-[var(--t-border)] bg-[var(--t-surface)]">
        <div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <a routerLink="/" class="flex items-center gap-3" aria-label="Transmuter home">
            <span class="relative flex h-10 w-10 items-center justify-center bg-[var(--t-primary)] text-white">
              <span class="absolute inset-y-1 left-3 w-1 bg-[var(--t-blue-light)]"></span>
              <span class="absolute inset-y-1 right-3 w-1 bg-[var(--t-blue-light)]"></span>
              <span class="relative text-sm font-black">T</span>
            </span>
            <span class="text-lg font-black uppercase">Transmuter</span>
          </a>
          <nav class="flex items-center gap-3">
            <a routerLink="/auth/login" class="btn-ghost px-4 py-2 text-xs font-black uppercase">Login</a>
            <a routerLink="/get-started" class="btn-primary px-4 py-2 text-xs">Get Started</a>
          </nav>
        </div>
      </header>

      <section class="mx-auto grid max-w-7xl gap-10 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
        <div>
          <p class="mb-5 text-xs font-black uppercase tracking-[0.3em] text-[var(--t-accent)]">
            Enterprise transformation control tower
          </p>
          <h1 class="max-w-4xl text-5xl font-black leading-[0.95] tracking-normal text-[var(--t-text-primary)] md:text-7xl">
            Run transformation like a value creation system.
          </h1>
          <p class="mt-8 max-w-2xl text-lg leading-8 text-[var(--t-text-secondary)]">
            Transmuter gives transformation offices one operating layer for initiatives,
            financial value, milestones, risks, KPIs, meetings, and AI-assisted portfolio intelligence.
          </p>
          <div class="mt-10 flex flex-wrap gap-3">
            <a routerLink="/get-started" class="btn-primary px-6 py-3 text-xs">Start subscription</a>
            <a routerLink="/auth/login" class="btn-ghost px-6 py-3 text-xs font-black uppercase">Login</a>
          </div>
        </div>

        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-6">
          <div class="border-b border-[var(--t-border)] pb-5">
            <p class="text-xs font-black uppercase tracking-[0.28em] text-[var(--t-accent)]">
              Our customer outcomes
            </p>
            <h2 class="mt-3 text-2xl font-black leading-tight text-[var(--t-text-primary)]">
              Case snapshots from transformation offices.
            </h2>
          </div>
          <div class="mt-6 space-y-5">
            @for (story of caseStudies; track story.customer) {
              <article class="border-b border-[var(--t-border)] pb-5 last:border-0 last:pb-0">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-black uppercase text-[var(--t-text-primary)]">{{ story.customer }}</p>
                    <p class="mt-1 text-[11px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      {{ story.sector }}
                    </p>
                  </div>
                  <p class="shrink-0 text-right text-2xl font-black text-[var(--t-accent)]">{{ story.value }}</p>
                </div>
                <p class="mt-4 text-sm leading-6 text-[var(--t-text-secondary)]">{{ story.copy }}</p>
                <div class="mt-4 grid grid-cols-3 gap-3">
                  @for (metric of story.metrics; track metric.label) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                      <p class="text-base font-black">{{ metric.value }}</p>
                      <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                        {{ metric.label }}
                      </p>
                    </div>
                  }
                </div>
              </article>
            }
          </div>
        </div>
      </section>

      <section class="border-y border-[var(--t-border)] bg-[var(--t-surface)]">
        <div class="mx-auto grid max-w-7xl gap-8 px-6 py-12 md:grid-cols-4">
          @for (benefit of benefits; track benefit.title) {
            <div>
              <p class="mb-3 text-sm font-black uppercase text-[var(--t-text-primary)]">{{ benefit.title }}</p>
              <p class="text-sm leading-6 text-[var(--t-text-secondary)]">{{ benefit.copy }}</p>
            </div>
          }
        </div>
      </section>
    </main>
  `,
})
export class HomeComponent {
  protected readonly caseStudies = [
    {
      customer: 'Northstar Manufacturing',
      sector: 'Industrial goods',
      value: '$18.4M',
      copy: 'Rebuilt a fragmented cost-out programme into one value register, giving the CFO a weekly view of committed savings, risks, and delayed benefits.',
      metrics: [
        { label: 'Run-rate value', value: '$18.4M' },
        { label: 'Cycle time cut', value: '32%' },
        { label: 'At-risk work', value: '-41%' },
      ],
    },
    {
      customer: 'Meridian Health Group',
      sector: 'Healthcare network',
      value: '$9.7M',
      copy: 'Connected initiative owners, PMO milestones, and KPI owners so integration synergy reporting matched what executives saw in steering committees.',
      metrics: [
        { label: 'Synergy tracked', value: '$9.7M' },
        { label: 'Gate decisions', value: '24' },
        { label: 'KPI coverage', value: '91%' },
      ],
    },
    {
      customer: 'Cobalt Retail Asia',
      sector: 'Consumer markets',
      value: '$14.2M',
      copy: 'Used portfolio AI to answer value leakage questions in minutes, then focused leadership attention on margin initiatives with weak milestone health.',
      metrics: [
        { label: 'Margin uplift', value: '$14.2M' },
        { label: 'Reports retired', value: '17' },
        { label: 'Review prep', value: '-6h' },
      ],
    },
  ];

  protected readonly benefits = [
    { title: 'Multi-tenant by design', copy: 'Each organization operates in its own tenant boundary with role-based access.' },
    { title: 'Transformation-office ready', copy: 'Built around initiatives, owners, workstreams, gates, and value bridge reporting.' },
    { title: 'Financial discipline', copy: 'Decimal-backed benefit and cost tracking keeps portfolio math inspectable.' },
    { title: 'Fast onboarding', copy: 'Start with a subscription, initial admin, and guided setup for the enterprise team.' },
  ];
}
