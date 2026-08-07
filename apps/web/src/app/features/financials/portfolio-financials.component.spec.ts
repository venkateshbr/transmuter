import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { ApiService } from '../../core/services/api.service';
import { PortfolioFinancialTrendComponent } from './portfolio-financial-trend.component';
import { PortfolioFinancialsComponent } from './portfolio-financials.component';

describe('PortfolioFinancialsComponent target summary', () => {
  it('renders the ACME baseline-to-target formulas without adding savings to gross margin', async () => {
    class TestResizeObserver {
      observe(): void {}
      disconnect(): void {}
    }
    Object.defineProperty(globalThis, 'ResizeObserver', {
      configurable: true,
      value: TestResizeObserver,
    });
    const get = vi.fn((path: string) => {
      if (path === '/financial-engine-configuration') {
        return of({ cost_categories: [], settings: { reporting_currency: 'USD' } });
      }
      if (path === '/governance/stage-gates') return of([]);
      if (path === '/financial-engine/annual-baselines') {
        return of({
          values: [
            { metric_key: 'annual_revenue_baseline', baseline_year: 2026, value: '20000000.0000' },
            { metric_key: 'annual_gross_margin_baseline', baseline_year: 2026, value: '9000000.0000' },
          ],
        });
      }
      if (path.startsWith('/portfolio/financials?')) {
        return of({
          granularity: 'monthly',
          reporting_currency: 'USD',
          selected_year: 2028,
          available_years: [2028],
          summary: [],
          periods: [],
          broader_period_totals: [],
          cost_breakdown: [],
          metric_breakdown: [],
          target_summary: {
            baseline_year: 2026,
            target_year: 2028,
            baseline_revenue: '20000000.0000',
            revenue_uplift_plan: '4000000.0000',
            target_revenue_plan: '24000000.0000',
            baseline_gross_margin: '9000000.0000',
            gross_margin_uplift_plan: '5432000.0000',
            target_gross_margin_plan: '14432000.0000',
            target_gross_margin_rate_plan: '60.1333',
          },
        });
      }
      if (path.startsWith('/portfolio/value-ramp?')) {
        return of({ periods: [], in_year: [] });
      }
      if (path.startsWith('/portfolio/value-bridge?')) {
        return of({
          basis: 'all_years',
          basis_label: 'All years',
          base_case: {},
          high_case: {},
          actual: {},
          rows: [],
        });
      }
      return of({});
    });

    await TestBed.configureTestingModule({
      imports: [PortfolioFinancialsComponent],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: { get, getBlob: vi.fn() } },
      ],
    })
      .overrideComponent(PortfolioFinancialTrendComponent, { set: { template: '' } })
      .compileComponents();

    const fixture = TestBed.createComponent(PortfolioFinancialsComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('[data-testid="target-revenue-card"]')?.textContent)
      .toContain('$24,000,000');
    expect(element.querySelector('[data-testid="target-revenue-card"]')?.textContent)
      .toContain('$20,000,000 baseline + $4,000,000 revenue uplift');
    expect(element.querySelector('[data-testid="target-gross-margin-card"]')?.textContent)
      .toContain('$14,432,000');
    expect(element.querySelector('[data-testid="target-gross-margin-card"]')?.textContent)
      .toContain('$9,000,000 baseline + $5,432,000 margin uplift');
    expect(element.querySelector('[data-testid="target-gross-margin-rate-card"]')?.textContent)
      .toContain('60.1%');
    expect(element.querySelector('[data-testid="portfolio-target-summary"]')?.textContent)
      .toContain('Cost savings contribute to Benefits and Net Run-rate Value');
  });
});
