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
import { Router, RouterLink } from '@angular/router';
import { echarts, type ECElementEvent, type EChartsCoreOption, type EChartsType } from '../../shared/charts/echarts-runtime';

type DashboardChartKind = 'stage' | 'rag' | 'pressure' | 'valueBridge' | 'riskHeatmap';

interface StageDefinition {
  id: string;
  label: string;
}

interface RiskHeatmapPoint {
  value: [number, number, number];
  impact: string;
  likelihood: string;
  itemStyle: { color: string };
}

@Component({
  selector: 'app-dashboard-echart-card',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <section
      class="card p-6"
      [class.cursor-pointer]="kind === 'pressure'"
      [attr.data-testid]="cardTestId()"
      [attr.role]="kind === 'pressure' ? 'button' : null"
      [attr.tabindex]="kind === 'pressure' ? 0 : null"
      [attr.aria-label]="kind === 'pressure' ? 'Open milestone tracker' : null"
      (click)="openPressure()"
      (keyup.enter)="openPressure()">
      <div class="mb-5 flex items-start justify-between gap-3">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">{{ eyebrow() }}</p>
          <h3 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ title() }}</h3>
        </div>
        <span class="material-icons text-[var(--t-text-tertiary)]" [title]="helpText()">help_outline</span>
      </div>

      <div
        #chartHost
        class="h-56 w-full"
        [class.h-48]="kind === 'pressure'"
        role="img"
        [attr.aria-label]="chartAriaLabel()"></div>

      @if (kind === 'stage') {
        <div class="mt-4 grid grid-cols-3 gap-2">
          @for (stage of stages; track stage.id) {
            <a
              routerLink="/initiatives/pipeline"
              [queryParams]="{ stage: stage.id }"
              [attr.data-testid]="'dashboard-stage-' + stage.id"
              class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2 text-center text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)] hover:border-[var(--t-accent)] hover:text-[var(--t-accent)]"
              [attr.aria-label]="'Open initiatives in ' + stage.label + ' stage'">
              {{ stage.label }}
            </a>
          }
        </div>
      }

      @if (kind === 'rag') {
        <div class="mt-4 grid grid-cols-3 gap-2">
          @for (rag of ragLevels; track rag) {
            <a
              routerLink="/initiatives/pipeline"
              [queryParams]="{ rag_status: rag }"
              [attr.data-testid]="'dashboard-rag-' + rag"
              class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2 text-center text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)] hover:border-[var(--t-accent)] hover:text-[var(--t-accent)]"
              [attr.aria-label]="'Open ' + rag + ' initiatives'">
              {{ rag }}
            </a>
          }
        </div>
      }

      @if (kind === 'valueBridge') {
        <a routerLink="/initiatives/pipeline" class="mt-4 inline-flex text-xs font-bold text-[var(--t-accent)]">
          Open financial initiatives
        </a>
      }

      @if (kind === 'riskHeatmap') {
        <div class="mt-4 grid grid-cols-3 gap-2">
          @for (impact of heatmapLevels; track impact) {
            @for (likelihood of heatmapLevels; track likelihood) {
              <a
                routerLink="/pmo/risks"
                [queryParams]="{ impact, likelihood }"
                [attr.data-testid]="'dashboard-risk-' + impact + '-' + likelihood"
                class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-2 py-2 text-center text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)] hover:border-[var(--t-accent)] hover:text-[var(--t-accent)]"
                [attr.aria-label]="'Open ' + impact + ' impact, ' + likelihood + ' likelihood risks'">
                {{ getHeatmapCount(impact, likelihood) }}
              </a>
            }
          }
        </div>
      }
    </section>
  `,
})
export class DashboardEchartCardComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) kind: DashboardChartKind = 'stage';
  @Input() data: any = null;
  @Input() stages: StageDefinition[] = [];
  @Input() heatmapLevels: string[] = ['high', 'medium', 'low'];

  @ViewChild('chartHost') private chartHost?: ElementRef<HTMLDivElement>;

  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);
  private chart?: EChartsType;
  private resizeObserver?: ResizeObserver;
  private themeObserver?: MutationObserver;

  readonly ragLevels = ['green', 'amber', 'red'];

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

  cardTestId(): string | null {
    if (this.kind === 'pressure') return 'dashboard-pressure';
    if (this.kind === 'valueBridge') return 'dashboard-value-bridge';
    if (this.kind === 'riskHeatmap') return 'dashboard-risk-heatmap';
    return null;
  }

  eyebrow(): string {
    switch (this.kind) {
      case 'stage': return 'Pipeline';
      case 'rag': return 'Portfolio Health';
      case 'pressure': return 'Delivery Load';
      case 'valueBridge': return 'Financial Value';
      case 'riskHeatmap': return 'Risk Exposure';
    }
  }

  title(): string {
    switch (this.kind) {
      case 'stage': return 'Pipeline by Stage';
      case 'rag': return 'Health Breakdown (RAG)';
      case 'pressure': return 'Portfolio Pressure';
      case 'valueBridge': return 'Value Bridge';
      case 'riskHeatmap': return 'Risk Heatmap';
    }
  }

  helpText(): string {
    switch (this.kind) {
      case 'stage': return 'Initiative count by delivery stage';
      case 'rag': return 'Green, amber, and red initiative health distribution';
      case 'pressure': return 'Portfolio pressure score based on delivery load';
      case 'valueBridge': return 'Portfolio benefits, costs, and net value';
      case 'riskHeatmap': return 'Open risks by impact and likelihood';
    }
  }

  chartAriaLabel(): string {
    return `${this.title()} chart`;
  }

  openPressure(): void {
    if (this.kind === 'pressure') {
      void this.router.navigate(['/progress']);
    }
  }

  getHeatmapCount(impact: string, likelihood: string): number {
    return Number(this.data?.risk_heatmap?.[`${impact}_${likelihood}`] || 0);
  }

  private renderChart(): void {
    if (!this.chart) return;

    const option = this.buildOption();
    this.chart.setOption(option, true);
  }

  private buildOption(): EChartsCoreOption {
    switch (this.kind) {
      case 'stage': return this.stageOption();
      case 'rag': return this.ragOption();
      case 'pressure': return this.pressureOption();
      case 'valueBridge': return this.valueBridgeOption();
      case 'riskHeatmap': return this.riskHeatmapOption();
    }
  }

  private stageOption(): EChartsCoreOption {
    const accent = this.cssVar('--t-accent');
    const accentSoft = this.cssVar('--t-accent-soft');
    const border = this.cssVar('--t-border');
    const textSecondary = this.cssVar('--t-text-secondary');
    const textTertiary = this.cssVar('--t-text-tertiary');
    const surface = this.cssVar('--t-surface');

    return {
      animationDuration: 320,
      aria: { enabled: true, decal: { show: true } },
      tooltip: this.tooltip(),
      grid: { left: 38, right: 12, top: 18, bottom: 42 },
      xAxis: {
        type: 'category',
        data: this.stages.map(stage => stage.label),
        axisLabel: { color: textSecondary, fontWeight: 700, interval: 0 },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        axisLabel: { color: textTertiary },
        splitLine: { lineStyle: { color: border, type: 'dashed' } },
      },
      series: [{
        name: 'Initiatives',
        type: 'bar',
        barMaxWidth: 42,
        itemStyle: { color: accent, borderColor: surface, borderWidth: 1 },
        emphasis: { itemStyle: { color: accentSoft, borderColor: accent, borderWidth: 2 } },
        data: this.stages.map(stage => ({
          value: Number(this.data?.pipeline_by_stage?.[stage.id] || 0),
          stageId: stage.id,
        })),
      }],
    };
  }

  private ragOption(): EChartsCoreOption {
    const textPrimary = this.cssVar('--t-text-primary');
    const textSecondary = this.cssVar('--t-text-secondary');

    return {
      animationDuration: 320,
      aria: { enabled: true, decal: { show: true } },
      tooltip: this.tooltip(),
      legend: {
        bottom: 0,
        textStyle: { color: textSecondary, fontFamily: 'Libre Franklin, Arial, sans-serif', fontWeight: 700 },
        icon: 'rect',
      },
      series: [{
        name: 'Initiatives',
        type: 'pie',
        radius: ['52%', '76%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: { color: textSecondary, formatter: '{b}: {c}', fontWeight: 700 },
        itemStyle: { borderColor: this.cssVar('--t-surface'), borderWidth: 3 },
        data: this.ragLevels.map(rag => ({
          name: rag,
          value: Number(this.data?.rag_breakdown?.[rag] || 0),
          rag,
          itemStyle: { color: this.ragColor(rag) },
        })),
      }],
      graphic: [{
        type: 'text',
        left: 'center',
        top: '39%',
        style: {
          text: `${this.healthScore()}%`,
          fill: textPrimary,
          font: '900 24px Libre Franklin, Arial, sans-serif',
          textAlign: 'center',
        },
      }],
    };
  }

  private pressureOption(): EChartsCoreOption {
    const score = Number(this.data?.portfolio_pressure?.score || 0);
    const label = this.data?.portfolio_pressure?.label || 'No pressure';
    const textPrimary = this.cssVar('--t-text-primary');
    const textSecondary = this.cssVar('--t-text-secondary');
    const border = this.cssVar('--t-border');
    const color = this.pressureColor(score);

    return {
      animationDuration: 320,
      aria: { enabled: true },
      series: [{
        name: 'Pressure',
        type: 'gauge',
        min: 0,
        max: 10,
        startAngle: 205,
        endAngle: -25,
        radius: '100%',
        center: ['50%', '62%'],
        progress: { show: true, width: 16, itemStyle: { color } },
        axisLine: { lineStyle: { width: 16, color: [[1, border]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { width: 4, length: '62%', itemStyle: { color: textPrimary } },
        anchor: { show: true, size: 8, itemStyle: { color: textPrimary } },
        detail: {
          formatter: () => `${score.toFixed(1)}\n${label}`,
          color: textPrimary,
          fontFamily: 'Libre Franklin, Arial, sans-serif',
          fontWeight: 900,
          fontSize: 22,
          lineHeight: 24,
          offsetCenter: [0, '45%'],
        },
        title: { color: textSecondary },
        data: [{ value: score, name: label }],
      }],
    };
  }

  private valueBridgeOption(): EChartsCoreOption {
    const accent = this.cssVar('--t-accent');
    const blueLight = this.cssVar('--t-blue-light');
    const green = this.cssVar('--t-green');
    const red = this.cssVar('--t-red');
    const border = this.cssVar('--t-border');
    const textSecondary = this.cssVar('--t-text-secondary');
    const textTertiary = this.cssVar('--t-text-tertiary');
    const bridge = this.data?.value_bridge || {};

    const values = [
      { name: 'Benefits Base', value: this.money(bridge.benefits_base), itemStyle: { color: blueLight } },
      { name: 'Benefits High', value: this.money(bridge.benefits_high), itemStyle: { color: accent } },
      { name: 'Costs Plan', value: -Math.abs(this.money(bridge.costs_plan)), itemStyle: { color: red } },
      { name: 'Net Base', value: this.money(bridge.net_base), itemStyle: { color: green } },
      { name: 'Net High', value: this.money(bridge.net_high), itemStyle: { color: accent } },
      { name: 'Net Actual', value: this.money(bridge.net_actual), itemStyle: { color: blueLight } },
    ];

    return {
      animationDuration: 320,
      aria: { enabled: true, decal: { show: true } },
      tooltip: this.tooltip(),
      grid: { left: 70, right: 16, top: 8, bottom: 46 },
      xAxis: {
        type: 'category',
        data: values.map(item => item.name),
        axisLabel: { color: textSecondary, fontWeight: 700, interval: 0, rotate: 24 },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: textTertiary, formatter: (value: string | number) => this.formatCompactMoney(Number(value)) },
        splitLine: { lineStyle: { color: border, type: 'dashed' } },
      },
      series: [{
        name: 'Value',
        type: 'bar',
        barMaxWidth: 34,
        data: values,
      }],
    };
  }

  private riskHeatmapOption(): EChartsCoreOption {
    const border = this.cssVar('--t-border');
    const textSecondary = this.cssVar('--t-text-secondary');
    const textPrimary = this.cssVar('--t-text-primary');
    const xLevels = ['low', 'medium', 'high'];
    const yLevels = ['low', 'medium', 'high'];
    const points: RiskHeatmapPoint[] = [];
    yLevels.forEach((impact, yIndex) => {
      xLevels.forEach((likelihood, xIndex) => {
        points.push({
          value: [xIndex, yIndex, this.getHeatmapCount(impact, likelihood)],
          impact,
          likelihood,
          itemStyle: { color: this.heatmapColor(impact, likelihood) },
        });
      });
    });

    return {
      animationDuration: 320,
      aria: { enabled: true, decal: { show: true } },
      tooltip: {
        ...this.tooltip(),
        formatter: (params: any) => {
          const point = params.data as RiskHeatmapPoint;
          return `${this.toTitle(point.impact)} impact / ${this.toTitle(point.likelihood)} likelihood: ${point.value[2]} risks`;
        },
      },
      grid: { left: 70, right: 16, top: 18, bottom: 40 },
      xAxis: {
        type: 'category',
        data: xLevels.map(level => this.toTitle(level)),
        axisLabel: { color: textSecondary, fontWeight: 700 },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: yLevels.map(level => this.toTitle(level)),
        axisLabel: { color: textSecondary, fontWeight: 700 },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      visualMap: { show: false, min: 0, max: Math.max(...points.map(point => point.value[2]), 1) },
      series: [{
        name: 'Risks',
        type: 'heatmap',
        data: points,
        label: { show: true, color: textPrimary, fontWeight: 900 },
        emphasis: { itemStyle: { borderColor: textPrimary, borderWidth: 2 } },
      }],
    };
  }

  private handleChartClick(params: ECElementEvent): void {
    const datum = params.data as any;
    if (this.kind === 'stage' && datum?.stageId) {
      void this.router.navigate(['/initiatives/pipeline'], { queryParams: { stage: datum.stageId } });
    }
    if (this.kind === 'rag' && datum?.rag) {
      void this.router.navigate(['/initiatives/pipeline'], { queryParams: { rag_status: datum.rag } });
    }
    if (this.kind === 'riskHeatmap' && datum?.impact && datum?.likelihood) {
      void this.router.navigate(['/pmo/risks'], { queryParams: { impact: datum.impact, likelihood: datum.likelihood } });
    }
  }

  private tooltip(): Record<string, unknown> {
    return {
      borderColor: this.cssVar('--t-border'),
      backgroundColor: this.cssVar('--t-surface'),
      textStyle: {
        color: this.cssVar('--t-text-primary'),
        fontFamily: 'Libre Franklin, Arial, sans-serif',
      },
      valueFormatter: (value: string | number) => {
        const numeric = Number(value);
        return Number.isFinite(numeric) && Math.abs(numeric) >= 1000 ? this.formatCompactMoney(numeric) : String(value);
      },
    };
  }

  private healthScore(): number {
    const total = Number(this.data?.summary?.total_initiatives || 0);
    if (!total) return 0;
    const red = Number(this.data?.rag_breakdown?.red || 0);
    return Math.round(((total - red) / total) * 100);
  }

  private ragColor(rag: string): string {
    if (rag === 'red') return this.cssVar('--t-red');
    if (rag === 'amber') return this.cssVar('--t-amber');
    return this.cssVar('--t-green');
  }

  private pressureColor(score: number): string {
    if (score < 3.4) return this.cssVar('--t-green');
    if (score < 6.7) return this.cssVar('--t-amber');
    return this.cssVar('--t-red');
  }

  private heatmapColor(impact: string, likelihood: string): string {
    const impactScore = impact === 'high' ? 3 : impact === 'medium' ? 2 : 1;
    const likelihoodScore = likelihood === 'high' ? 3 : likelihood === 'medium' ? 2 : 1;
    const score = impactScore * likelihoodScore;
    if (score >= 9) return this.cssVar('--t-red');
    if (score >= 6) return this.cssVar('--t-red');
    if (score >= 4) return this.cssVar('--t-amber');
    return this.cssVar('--t-green');
  }

  private cssVar(name: string): string {
    const value = this.document.defaultView
      ?.getComputedStyle(this.document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || 'currentColor';
  }

  private money(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = typeof value === 'string' ? Number(value) : value;
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private formatCompactMoney(value: number): string {
    return new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value);
  }

  private toTitle(value: string): string {
    return value.slice(0, 1).toUpperCase() + value.slice(1);
  }
}
