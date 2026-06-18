import { CommonModule, DOCUMENT, isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  PLATFORM_ID,
  ViewChild,
  inject,
} from '@angular/core';
import { echarts, type EChartsCoreOption, type EChartsType } from '../../charts/echarts-runtime';

interface PnlBridgeStep {
  key: string;
  label: string;
  value: string;
  cumulative_value: string;
  step_kind: 'baseline' | 'increase' | 'decrease' | 'subtotal' | 'target';
  display_order: number;
}

interface PnlBridgeCase {
  label: string;
  target_revenue: string;
  target_run_rate_value: string;
  incremental_net_run_rate: string;
  one_off_costs: string;
  steps: PnlBridgeStep[];
}

interface PnlBridge {
  baseline_year: number | null;
  base_case: PnlBridgeCase;
}

@Component({
  selector: 'app-value-waterfall',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="card p-6" data-testid="initiative-pnl-bridge">
      <div class="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
            Baseline to Target
          </p>
          <h3 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">
            Initiative P&amp;L Bridge<span class="text-[var(--t-accent)]">.</span>
          </h3>
          <p class="mt-2 max-w-2xl text-xs font-medium leading-relaxed text-[var(--t-text-secondary)]">
            Baseline operating values, initiative uplift, recurring run cost, and target run-rate value.
          </p>
        </div>

        @if (bridgeCase()) {
          <div class="grid min-w-[280px] grid-cols-2 gap-2 text-right">
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Baseline Year</p>
              <p class="text-sm font-black text-[var(--t-text-primary)]">FY{{ pnlBridge()?.baseline_year || 'n/a' }}</p>
            </div>
            <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Scenario</p>
              <p class="text-sm font-black text-[var(--t-text-primary)]">{{ bridgeCase()?.label || 'Plan Base' }}</p>
            </div>
          </div>
        }
      </div>

      <div class="relative">
        <div
          #chartHost
          class="h-72 w-full"
          role="img"
          aria-label="Initiative baseline to target P and L bridge"></div>

        @if (!hasBridgeData()) {
          <div class="absolute inset-0 flex flex-col items-center justify-center border border-dashed border-[var(--t-border)] bg-[var(--t-surface)] text-center">
            <span class="material-icons mb-2 text-4xl text-[var(--t-text-tertiary)]">waterfall_chart</span>
            <p class="text-sm font-bold text-[var(--t-text-primary)]">No P&amp;L bridge data available</p>
            <p class="mt-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--t-text-tertiary)]">
              Add annual baselines and configurable financial values.
            </p>
          </div>
        }
      </div>

      @if (hasBridgeData()) {
        <div class="mt-5 grid gap-3 sm:grid-cols-3">
          <div class="border-l-4 border-[var(--t-blue-light)] bg-[var(--t-surface-raised)] px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Target Revenue</p>
            <p class="mt-1 text-base font-black text-[var(--t-text-primary)]">{{ formatMoneyValue(bridgeCase()?.target_revenue) }}</p>
          </div>
          <div class="border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Target Run-rate Value</p>
            <p class="mt-1 text-base font-black text-[var(--t-text-primary)]">{{ formatMoneyValue(bridgeCase()?.target_run_rate_value) }}</p>
          </div>
          <div class="border-l-4 border-[var(--t-border-strong)] bg-[var(--t-surface-raised)] px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Incremental Net Impact</p>
            <p class="mt-1 text-base font-black text-[var(--t-accent)]">{{ formatMoneyValue(bridgeCase()?.incremental_net_run_rate) }}</p>
            <p class="mt-1 text-[10px] font-bold text-[var(--t-text-tertiary)]">
              One-off investment {{ formatMoneyValue(bridgeCase()?.one_off_costs) }}
            </p>
          </div>
        </div>
      }
    </section>
  `,
})
export class ValueWaterfallComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() data: any = null;

  @ViewChild('chartHost') private chartHost?: ElementRef<HTMLDivElement>;

  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);
  private chart?: EChartsType;
  private resizeObserver?: ResizeObserver;
  private themeObserver?: MutationObserver;

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    const host = this.chartHost?.nativeElement;
    if (!host) return;
    this.chart = echarts.init(host, null, { renderer: 'canvas' });
    this.resizeObserver = new ResizeObserver(() => this.chart?.resize());
    this.resizeObserver.observe(host);
    this.themeObserver = new MutationObserver(() => this.renderChart());
    this.themeObserver.observe(this.document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
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

  pnlBridge(): PnlBridge | null {
    return this.data?.pnl_bridge || null;
  }

  bridgeCase(): PnlBridgeCase | null {
    return this.pnlBridge()?.base_case || null;
  }

  hasBridgeData(): boolean {
    return (this.bridgeCase()?.steps || []).length > 0;
  }

  formatMoneyValue(value: string | number | null | undefined): string {
    return this.formatMoney(this.money(value));
  }

  private renderChart(): void {
    if (!this.chart) return;
    if (!this.hasBridgeData()) {
      this.chart.clear();
      return;
    }
    this.chart.setOption(this.buildOption(), true);
  }

  private buildOption(): EChartsCoreOption {
    const textPrimary = this.cssVar('--t-text-primary');
    const textSecondary = this.cssVar('--t-text-secondary');
    const textTertiary = this.cssVar('--t-text-tertiary');
    const border = this.cssVar('--t-border');
    const transparent = 'rgba(0,0,0,0)';
    const bars = this.waterfallBars();

    return {
      animationDuration: 320,
      aria: { enabled: true, decal: { show: true } },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        borderColor: border,
        backgroundColor: this.cssVar('--t-surface'),
        textStyle: { color: textPrimary, fontFamily: 'Libre Franklin, Arial, sans-serif' },
        formatter: (params: unknown) => this.tooltip(params),
      },
      grid: { left: 76, right: 20, top: 18, bottom: 64 },
      xAxis: {
        type: 'category',
        data: bars.map(item => item.label),
        axisLabel: {
          color: textSecondary,
          fontSize: 10,
          fontWeight: 700,
          interval: 0,
          rotate: 22,
        },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: textTertiary,
          formatter: (value: string | number) => this.formatCompactMoney(Number(value)),
        },
        splitLine: { lineStyle: { color: border, type: 'dashed' } },
      },
      series: [
        {
          name: 'Offset',
          type: 'bar',
          stack: 'bridge',
          silent: true,
          itemStyle: { color: transparent, borderColor: transparent },
          emphasis: { disabled: true },
          data: bars.map(item => item.offset),
        },
        {
          name: 'Value',
          type: 'bar',
          stack: 'bridge',
          barMaxWidth: 36,
          label: {
            show: true,
            position: 'top',
            color: textPrimary,
            fontSize: 10,
            fontWeight: 800,
            formatter: (params: { dataIndex: number }) =>
              this.formatCompactMoney(bars[params.dataIndex]?.displayValue || 0),
          },
          data: bars.map(item => ({
            value: item.height,
            itemStyle: { color: item.color },
            _bridgeValue: item.displayValue,
            _bridgeCumulative: item.cumulative,
          })),
        },
      ],
    };
  }

  private waterfallBars(): Array<{
    label: string;
    offset: number;
    height: number;
    displayValue: number;
    cumulative: number;
    color: string;
  }> {
    let current = 0;
    return (this.bridgeCase()?.steps || []).map(step => {
      const value = this.money(step.value);
      let offset = 0;
      let height = Math.abs(value);
      if (step.step_kind === 'increase' || step.step_kind === 'decrease') {
        const next = current + value;
        offset = Math.min(current, next);
        height = Math.abs(value);
        current = next;
      } else {
        current = value;
      }
      return {
        label: step.label,
        offset,
        height,
        displayValue: value,
        cumulative: current,
        color: this.stepColor(step),
      };
    });
  }

  private stepColor(step: PnlBridgeStep): string {
    if (step.step_kind === 'decrease') return this.cssVar('--t-red');
    if (step.step_kind === 'target') return this.cssVar('--t-green');
    if (step.step_kind === 'baseline') return this.cssVar('--t-primary');
    return this.cssVar('--t-blue-light');
  }

  private tooltip(params: unknown): string {
    const items = Array.isArray(params) ? params as Array<any> : [params as any];
    const valueItem = items.find(item => item?.seriesName === 'Value');
    const step = (this.bridgeCase()?.steps || [])[Number(valueItem?.dataIndex ?? 0)];
    if (!step) return '';
    return [
      `<strong>${step.label}</strong>`,
      `Value: ${this.formatMoneyValue(step.value)}`,
      `Bridge total: ${this.formatMoneyValue(step.cumulative_value)}`,
    ].join('<br/>');
  }

  private cssVar(name: string): string {
    if (!isPlatformBrowser(this.platformId)) return '';
    return getComputedStyle(this.document.documentElement).getPropertyValue(name).trim();
  }

  private money(value: string | number | null | undefined): number {
    const parsed = Number(value || 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private formatMoney(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  }

  private formatCompactMoney(value: number): string {
    const abs = Math.abs(value);
    if (abs >= 1_000_000_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000_000_000).toFixed(1)}B`;
    if (abs >= 1_000_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000_000).toFixed(1)}M`;
    if (abs >= 1_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000).toFixed(0)}K`;
    return this.formatMoney(value);
  }
}
