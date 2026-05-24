import { CommonModule, DOCUMENT, isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  PLATFORM_ID,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { echarts, type ECElementEvent, type EChartsCoreOption, type EChartsType } from '../../shared/charts/echarts-runtime';

type FinancialTrendMetric = 'net_value' | 'total_costs' | 'benefits';

export type FinancialTrendGranularity = 'monthly' | 'quarterly' | 'yearly';

export interface FinancialTrendRow {
  period: string;
  net_value_plan: string;
  net_value_actual: string;
  total_costs_plan: string;
  total_costs_actual: string;
  benefits_plan: string;
  benefits_actual: string;
}

interface TrendMetricOption {
  id: FinancialTrendMetric;
  label: string;
  planKey: keyof FinancialTrendRow;
  actualKey: keyof FinancialTrendRow;
}

@Component({
  selector: 'app-portfolio-financial-trend',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="card overflow-hidden p-0">
      <div class="grid gap-4 border-b border-[var(--t-border)] p-5 xl:grid-cols-[1fr_auto] xl:items-end">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Apache ECharts Pilot</p>
          <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Financial Trend</h2>
          <p class="mt-2 max-w-2xl text-xs leading-5 text-[var(--t-text-secondary)]">
            Plan and actual trajectory by period, using the same portfolio financials data as the reconciliation table.
          </p>
        </div>
        <div class="inline-flex border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-1" aria-label="Trend metric">
          @for (option of metricOptions; track option.id) {
            <button
              type="button"
              class="px-3 py-2 text-[10px] font-black uppercase tracking-widest"
              [class.bg-[var(--t-primary)]]="metric() === option.id"
              [class.text-white]="metric() === option.id"
              [class.text-[var(--t-text-secondary)]]="metric() !== option.id"
              [attr.aria-pressed]="metric() === option.id"
              (click)="setMetric(option.id)">
              {{ option.label }}
            </button>
          }
        </div>
      </div>

      <div class="grid gap-0 lg:grid-cols-[minmax(0,1fr)_220px]">
        <div class="relative min-h-[320px] border-b border-[var(--t-border)] lg:border-b-0 lg:border-r">
          <div
            #chartHost
            class="h-[320px] w-full"
            role="img"
            [attr.aria-label]="chartAriaLabel()"></div>
          @if (!rows.length) {
            <div class="absolute inset-0 flex items-center justify-center bg-[var(--t-surface)] px-6 text-center text-sm font-bold text-[var(--t-text-secondary)]">
              No period data is available for the current filters.
            </div>
          }
        </div>

        <aside class="grid content-start gap-4 bg-[var(--t-surface-raised)] p-5">
          <div>
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Current View</p>
            <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ activeMetric().label }}</p>
            <p class="mt-1 text-xs font-bold capitalize text-[var(--t-text-secondary)]">{{ granularity }}</p>
          </div>
          <div class="border-t border-[var(--t-border)] pt-4">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Latest Period</p>
            <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ latestPeriodLabel() }}</p>
            <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">{{ latestPlanLabel() }} plan</p>
            @if (showActuals) {
              <p class="mt-1 text-xs font-bold text-[var(--t-accent)]">{{ latestActualLabel() }} actual</p>
            }
          </div>
          <p class="border-t border-[var(--t-border)] pt-4 text-[10px] font-bold uppercase leading-5 tracking-widest text-[var(--t-text-tertiary)]">
            Select a point to inspect contributing initiatives.
          </p>
        </aside>
      </div>
    </section>
  `,
})
export class PortfolioFinancialTrendComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() rows: FinancialTrendRow[] = [];
  @Input() granularity: FinancialTrendGranularity = 'monthly';
  @Input() showActuals = false;

  @Output() readonly periodSelected = new EventEmitter<FinancialTrendRow>();

  @ViewChild('chartHost') private chartHost?: ElementRef<HTMLDivElement>;

  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);
  private chart?: EChartsType;
  private resizeObserver?: ResizeObserver;
  private themeObserver?: MutationObserver;

  readonly metric = signal<FinancialTrendMetric>('net_value');
  readonly metricOptions: TrendMetricOption[] = [
    { id: 'net_value', label: 'Net Value', planKey: 'net_value_plan', actualKey: 'net_value_actual' },
    { id: 'total_costs', label: 'Costs', planKey: 'total_costs_plan', actualKey: 'total_costs_actual' },
    { id: 'benefits', label: 'Benefits', planKey: 'benefits_plan', actualKey: 'benefits_actual' },
  ];

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    const host = this.chartHost?.nativeElement;
    if (!host) return;

    this.chart = echarts.init(host, null, { renderer: 'canvas' });
    this.chart.on('click', params => this.handleChartClick(params as ECElementEvent));
    this.resizeObserver = new ResizeObserver(() => this.chart?.resize());
    this.resizeObserver.observe(host);
    this.themeObserver = new MutationObserver(() => this.renderChart());
    this.themeObserver.observe(this.document.documentElement, { attributes: true, attributeFilter: ['class'] });
    this.renderChart();
  }

  ngOnChanges(): void {
    this.renderChart();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.themeObserver?.disconnect();
    this.chart?.dispose();
  }

  setMetric(value: FinancialTrendMetric): void {
    this.metric.set(value);
    this.renderChart();
  }

  activeMetric(): TrendMetricOption {
    return this.metricOptions.find(option => option.id === this.metric()) || this.metricOptions[0];
  }

  chartAriaLabel(): string {
    const metric = this.activeMetric().label.toLowerCase();
    return `${metric} trend chart across ${this.rows.length} ${this.granularity} periods`;
  }

  latestPeriodLabel(): string {
    return this.latestRow()?.period || 'No periods';
  }

  latestPlanLabel(): string {
    const row = this.latestRow();
    return row ? this.formatMoney(row[this.activeMetric().planKey]) : '$0';
  }

  latestActualLabel(): string {
    const row = this.latestRow();
    return row ? this.formatMoney(row[this.activeMetric().actualKey]) : '$0';
  }

  private renderChart(): void {
    if (!this.chart) return;

    const metric = this.activeMetric();
    const textPrimary = this.cssVar('--t-text-primary');
    const textSecondary = this.cssVar('--t-text-secondary');
    const textTertiary = this.cssVar('--t-text-tertiary');
    const border = this.cssVar('--t-border');
    const surface = this.cssVar('--t-surface');
    const accent = this.cssVar('--t-accent');
    const accentSoft = this.cssVar('--t-accent-soft');
    const red = this.cssVar('--t-red');

    const planData = this.rows.map(row => this.parseMoney(row[metric.planKey]));
    const actualData = this.rows.map(row => this.parseMoney(row[metric.actualKey]));
    const series: Record<string, unknown>[] = [
      {
        name: 'Plan',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 3, color: accent },
        itemStyle: { color: accent, borderColor: surface, borderWidth: 2 },
        areaStyle: { color: accentSoft },
        emphasis: { focus: 'series' },
        data: planData,
      },
    ];

    if (this.showActuals) {
      series.push({
        name: 'Actual',
        type: 'line',
        smooth: true,
        symbol: 'diamond',
        symbolSize: 8,
        lineStyle: { width: 2, color: red, type: 'dashed' },
        itemStyle: { color: red, borderColor: surface, borderWidth: 2 },
        emphasis: { focus: 'series' },
        data: actualData,
      });
    }

    const option: EChartsCoreOption = {
      animationDuration: 320,
      aria: {
        enabled: true,
        decal: { show: true },
      },
      color: [accent, red],
      tooltip: {
        trigger: 'axis',
        borderColor: border,
        backgroundColor: surface,
        textStyle: { color: textPrimary, fontFamily: 'Libre Franklin, Arial, sans-serif' },
        valueFormatter: (value: string | number) => this.formatMoney(value),
      },
      legend: {
        top: 16,
        right: 20,
        textStyle: { color: textSecondary, fontFamily: 'Libre Franklin, Arial, sans-serif', fontWeight: 700 },
        icon: 'rect',
      },
      grid: {
        left: 72,
        right: 28,
        top: 62,
        bottom: 54,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: this.rows.map(row => row.period),
        axisLabel: { color: textSecondary, fontWeight: 700 },
        axisLine: { lineStyle: { color: border } },
        axisTick: { lineStyle: { color: border } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: textTertiary,
          formatter: (value: string | number) => this.formatCompactMoney(Number(value)),
        },
        splitLine: { lineStyle: { color: border, type: 'dashed' } },
      },
      series,
      graphic: this.rows.length
        ? []
        : [{
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: 'No data',
              fill: textSecondary,
              font: '700 13px Libre Franklin, Arial, sans-serif',
            },
          }],
    };

    this.chart.setOption(option, true);
  }

  private handleChartClick(params: ECElementEvent): void {
    if (typeof params.dataIndex !== 'number') return;
    const row = this.rows[params.dataIndex];
    if (row) this.periodSelected.emit(row);
  }

  private latestRow(): FinancialTrendRow | null {
    return this.rows.length ? this.rows[this.rows.length - 1] : null;
  }

  private cssVar(name: string): string {
    const value = this.document.defaultView
      ?.getComputedStyle(this.document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || 'currentColor';
  }

  private parseMoney(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = typeof value === 'string' ? Number(value) : value;
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(this.parseMoney(value));
  }

  private formatCompactMoney(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value);
  }
}
