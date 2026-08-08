import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import {
  RoadmapDependency,
  RoadmapInitiative,
  RoadmapLinkMode,
  RoadmapMilestone,
  RoadmapZoom,
} from './roadmap.models';

type TimelineRowKind = 'workstream' | 'initiative' | 'milestone';

interface TimelineRow {
  id: string;
  kind: TimelineRowKind;
  label: string;
  meta: string;
  top: number;
  height: number;
  milestone: RoadmapMilestone | null;
  startX: number;
  endX: number;
  width: number;
  point: boolean;
  inTrace: boolean | null;
}

interface TimelineTick {
  id: string;
  label: string;
  left: number;
}

interface TimelineLink {
  id: string;
  path: string;
  status: RoadmapDependency['status'];
  marker: string;
}

const DAY_MS = 86_400_000;
const LABEL_WIDTH = 330;

@Component({
  selector: 'app-roadmap-gantt',
  standalone: true,
  template: `
    <div
      #scroller
      class="roadmap-chart"
      data-testid="roadmap-gantt"
      role="region"
      aria-label="Portfolio milestone Gantt chart. Scroll horizontally to review the full schedule."
      tabindex="0">
      <div class="roadmap-canvas" [style.width.px]="canvasWidth">
        <header class="roadmap-axis" [style.--timeline-width]="timelineWidth + 'px'">
          <div class="roadmap-axis-register">
            <span>Milestone register</span>
            <small>{{ plottedMilestoneCount }} scheduled</small>
          </div>
          <div class="roadmap-axis-timeline" [style.width.px]="timelineWidth">
            @for (tick of ticks; track tick.id) {
              <div class="roadmap-axis-tick" [style.left.px]="tick.left">
                <span>{{ tick.label }}</span>
              </div>
            }
          </div>
        </header>

        <div class="roadmap-body" [style.height.px]="bodyHeight">
          <svg
            class="roadmap-links"
            [attr.width]="timelineWidth"
            [attr.height]="bodyHeight"
            [attr.viewBox]="'0 0 ' + timelineWidth + ' ' + bodyHeight"
            aria-hidden="true">
            <defs>
              <marker id="roadmap-arrow-default" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--t-accent)" />
              </marker>
              <marker id="roadmap-arrow-risk" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--t-amber)" />
              </marker>
              <marker id="roadmap-arrow-blocking" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--t-red)" />
              </marker>
              <marker id="roadmap-arrow-resolved" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--t-text-tertiary)" />
              </marker>
            </defs>
            @for (link of links; track link.id) {
              <path
                class="roadmap-link"
                [class.roadmap-link-risk]="link.status === 'at_risk'"
                [class.roadmap-link-blocking]="link.status === 'blocking'"
                [class.roadmap-link-resolved]="link.status === 'resolved'"
                [attr.d]="link.path"
                [attr.marker-end]="link.marker" />
            }
          </svg>

          @if (todayX !== null) {
            <div class="roadmap-today" [style.left.px]="labelWidth + todayX">
              <span>Today</span>
            </div>
          }

          @for (row of rows; track row.id) {
            <div
              class="roadmap-row"
              [class.roadmap-workstream-row]="row.kind === 'workstream'"
              [class.roadmap-initiative-row]="row.kind === 'initiative'"
              [class.roadmap-milestone-row]="row.kind === 'milestone'"
              [class.roadmap-row-dimmed]="row.inTrace === false"
              [style.top.px]="row.top"
              [style.height.px]="row.height"
              [style.--timeline-width]="timelineWidth + 'px'">
              <div class="roadmap-register-cell">
                @if (row.kind === 'workstream') {
                  <span class="material-icons" aria-hidden="true">view_timeline</span>
                  <strong>{{ row.label }}</strong>
                } @else if (row.kind === 'initiative') {
                  <span class="roadmap-initiative-code">{{ row.meta }}</span>
                  <strong>{{ row.label }}</strong>
                } @else if (row.milestone; as milestone) {
                  <button
                    type="button"
                    class="roadmap-row-button"
                    [attr.data-roadmap-row-label]="milestone.id"
                    (click)="select(milestone.id)"
                    [attr.aria-label]="'Open milestone details for ' + milestone.name">
                    <span>{{ milestone.name }}</span>
                    <small>{{ milestone.owner_name || 'Unassigned' }} · {{ dateLabel(milestone) }}</small>
                  </button>
                }
              </div>
              <div class="roadmap-timeline-cell" [style.width.px]="timelineWidth">
                @if (row.milestone; as milestone) {
                  <button
                    type="button"
                    class="roadmap-bar"
                    data-roadmap-milestone
                    [attr.data-milestone-id]="milestone.id"
                    [class.roadmap-bar-point]="row.point"
                    [class.roadmap-bar-complete]="milestone.status === 'complete'"
                    [class.roadmap-bar-overdue]="milestone.status === 'overdue'"
                    [class.roadmap-bar-in-progress]="milestone.status === 'in_progress'"
                    [class.roadmap-bar-selected]="milestone.id === selectedMilestoneId"
                    [style.left.px]="row.startX"
                    [style.width.px]="row.width"
                    (click)="select(milestone.id)"
                    [title]="tooltip(milestone)"
                    [attr.aria-label]="tooltip(milestone)">
                    @if (!row.point) { <span>{{ milestone.name }}</span> }
                  </button>
                }
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 560px; }
    .roadmap-chart { width: 100%; max-height: min(72vh, 820px); min-height: 560px; overflow: auto; background: var(--t-surface); outline: none; }
    .roadmap-chart:focus-visible { box-shadow: inset 0 0 0 2px var(--t-accent); }
    .roadmap-canvas { position: relative; min-height: 560px; color: var(--t-text-primary); font-family: "Libre Franklin", Arial, sans-serif; }
    .roadmap-body { position: relative; }
    .roadmap-row { position: absolute; left: 0; display: grid; grid-template-columns: ${LABEL_WIDTH}px var(--timeline-width); width: 100%; border-bottom: 1px solid var(--t-border); transition: opacity .15s ease; }
    .roadmap-register-cell { position: sticky; left: 0; z-index: 7; display: flex; align-items: center; min-width: 0; padding: 0 1rem; background: var(--t-surface); border-right: 1px solid var(--t-border-strong); }
    .roadmap-timeline-cell { position: relative; background-color: var(--t-surface); background-image: repeating-linear-gradient(90deg, transparent 0, transparent 89px, var(--t-border) 90px); }
    .roadmap-milestone-row:hover .roadmap-register-cell, .roadmap-milestone-row:hover .roadmap-timeline-cell { background-color: color-mix(in srgb, var(--t-accent-soft) 45%, var(--t-surface)); }
    .roadmap-row-button { width: 100%; min-width: 0; padding-left: 1.35rem; text-align: left; color: var(--t-text-primary); }
    .roadmap-row-button span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .7rem; font-weight: 850; }
    .roadmap-row-button small { display: block; margin-top: .18rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--t-text-tertiary); font-size: .55rem; font-weight: 650; }
    .roadmap-row-button:hover span { color: var(--t-accent); text-decoration: underline; text-underline-offset: 3px; }
    .roadmap-row-button:focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
    .roadmap-bar { position: absolute; top: 50%; z-index: 5; height: 18px; transform: translateY(-50%); overflow: hidden; border: 1px solid color-mix(in srgb, var(--t-accent) 76%, black); border-radius: 0; background: var(--t-accent); color: white; box-shadow: 0 2px 5px rgba(7,31,60,.18); text-align: left; cursor: pointer; }
    .roadmap-bar::after { content: ""; position: absolute; right: -1px; top: 3px; width: 10px; height: 10px; transform: rotate(45deg) translate(2px,-2px); background: inherit; border: 1px solid rgba(255,255,255,.65); }
    .roadmap-bar span { display: block; overflow: hidden; padding: 0 17px 0 7px; text-overflow: ellipsis; white-space: nowrap; font-size: .55rem; font-weight: 850; line-height: 16px; }
    .roadmap-bar:hover { filter: brightness(1.08); box-shadow: 0 3px 9px rgba(7,31,60,.28); }
    .roadmap-bar:focus-visible, .roadmap-bar-selected { outline: 3px solid var(--t-blue-light); outline-offset: 2px; }
    .roadmap-bar-point { width: 14px !important; height: 14px; overflow: visible; border: 0; clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); }
    .roadmap-bar-point::after { display: none; }
    .roadmap-bar-complete { border-color: var(--t-text-tertiary); background: var(--t-text-tertiary); }
    .roadmap-bar-overdue { border-color: var(--t-red); background: var(--t-red); }
    .roadmap-bar-in-progress { border-color: var(--t-accent); background: var(--t-accent); }
    .roadmap-links { position: absolute; z-index: 4; left: ${LABEL_WIDTH}px; top: 0; overflow: visible; pointer-events: none; }
    .roadmap-link { fill: none; stroke: var(--t-accent); stroke-width: 1.6; opacity: .8; }
    .roadmap-link-risk { stroke: var(--t-amber); stroke-width: 2; }
    .roadmap-link-blocking { stroke: var(--t-red); stroke-width: 2.4; }
    .roadmap-link-resolved { stroke: var(--t-text-tertiary); opacity: .4; }
    .roadmap-today { position: absolute; z-index: 6; inset-block: 0; width: 1px; border-left: 1px dashed var(--t-red); pointer-events: none; }
    .roadmap-today span { position: sticky; top: 63px; display: inline-block; transform: translateX(-50%); background: var(--t-red); padding: .15rem .35rem; color: white; font-size: .5rem; font-weight: 900; text-transform: uppercase; letter-spacing: .08em; }
    .roadmap-row-dimmed { opacity: .18; }
    @media (prefers-reduced-motion: reduce) { .roadmap-row { transition: none; } }
  `],
})
export class RoadmapGanttComponent implements AfterViewInit, OnChanges {
  @ViewChild('scroller', { static: true }) private scroller!: ElementRef<HTMLDivElement>;
  @Input() milestones: RoadmapMilestone[] = [];
  @Input() initiatives: RoadmapInitiative[] = [];
  @Input() dependencies: RoadmapDependency[] = [];
  @Input() zoom: RoadmapZoom = 'quarter';
  @Input() linkMode: RoadmapLinkMode = 'all';
  @Input() selectedMilestoneId: string | null = null;
  @Output() milestoneSelected = new EventEmitter<string>();

  readonly labelWidth = LABEL_WIDTH;
  rows: TimelineRow[] = [];
  ticks: TimelineTick[] = [];
  links: TimelineLink[] = [];
  timelineWidth = 900;
  bodyHeight = 0;
  todayX: number | null = null;
  private rangeStart = 0;
  private rangeEnd = 1;
  private fitToContainer = false;

  get canvasWidth(): number { return LABEL_WIDTH + this.timelineWidth; }
  get plottedMilestoneCount(): number { return this.rows.filter(row => row.kind === 'milestone').length; }

  ngAfterViewInit(): void { this.rebuild(); }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['zoom'] && !changes['zoom'].firstChange) this.fitToContainer = false;
    this.rebuild();
  }

  fitAll(): void {
    this.fitToContainer = true;
    this.rebuild();
    this.scroller.nativeElement.scrollLeft = 0;
  }

  showToday(): void {
    if (this.todayX === null) return;
    const element = this.scroller.nativeElement;
    element.scrollLeft = Math.max(0, LABEL_WIDTH + this.todayX - element.clientWidth / 2);
  }

  select(id: string): void { this.milestoneSelected.emit(id); }

  dateLabel(milestone: RoadmapMilestone): string {
    if (milestone.planned_start && milestone.planned_end && milestone.planned_start !== milestone.planned_end) {
      return `${this.shortDate(milestone.planned_start)} – ${this.shortDate(milestone.planned_end)}`;
    }
    return this.shortDate(milestone.planned_end || milestone.planned_start || '');
  }

  tooltip(milestone: RoadmapMilestone): string {
    return `Open ${milestone.name}. ${this.dateLabel(milestone)}. ${milestone.owner_name || 'Owner not assigned'}.`;
  }

  private rebuild(): void {
    const scheduled = this.milestones
      .filter(item => !!(item.planned_start || item.planned_end))
      .sort((a, b) => {
        const workstream = (a.workstream_name || '').localeCompare(b.workstream_name || '');
        if (workstream) return workstream;
        const initiative = (a.initiative_name || '').localeCompare(b.initiative_name || '');
        if (initiative) return initiative;
        return (a.planned_start || a.planned_end || '').localeCompare(b.planned_start || b.planned_end || '');
      });
    if (!scheduled.length) {
      this.rows = [];
      this.ticks = [];
      this.links = [];
      this.bodyHeight = 0;
      this.todayX = null;
      return;
    }

    const dates = scheduled.flatMap(item => [item.planned_start, item.planned_end].filter((value): value is string => !!value).map(value => this.dateMs(value)));
    const rawStart = Math.min(...dates);
    const rawEnd = Math.max(...dates);
    const rawSpan = Math.max(DAY_MS, rawEnd - rawStart);
    const padding = Math.max(7 * DAY_MS, rawSpan * .035);
    this.rangeStart = rawStart - padding;
    this.rangeEnd = rawEnd + padding;
    this.timelineWidth = this.calculateWidth((this.rangeEnd - this.rangeStart) / DAY_MS);
    this.ticks = this.buildTicks();

    const candidateLinks = this.dependencies.filter(link => scheduled.some(item => item.id === link.source) && scheduled.some(item => item.id === link.target));
    const traceIds = this.traceIds(candidateLinks);
    const initiativeLookup = new Map(this.initiatives.map(item => [item.id, item]));
    const rows: TimelineRow[] = [];
    let top = 0;
    let activeWorkstream = '';
    let activeInitiative = '';
    for (const milestone of scheduled) {
      const initiative = initiativeLookup.get(milestone.initiative_id);
      const workstream = milestone.workstream_name || initiative?.workstream_name || 'Unassigned workstream';
      if (workstream !== activeWorkstream) {
        activeWorkstream = workstream;
        activeInitiative = '';
        rows.push(this.headingRow(`ws:${workstream}`, 'workstream', workstream, '', top, 34));
        top += 34;
      }
      if (milestone.initiative_id !== activeInitiative) {
        activeInitiative = milestone.initiative_id;
        rows.push(this.headingRow(
          `init:${milestone.initiative_id}`,
          'initiative',
          milestone.initiative_name || initiative?.name || 'Unassigned initiative',
          milestone.initiative_code || initiative?.initiative_code || 'INIT',
          top,
          38,
        ));
        top += 38;
      }
      const start = this.dateMs(milestone.planned_start || milestone.planned_end as string);
      const end = this.dateMs(milestone.planned_end || milestone.planned_start as string);
      const startX = this.x(start);
      const endX = this.x(end + DAY_MS);
      const point = !milestone.planned_start || !milestone.planned_end || milestone.planned_start === milestone.planned_end;
      rows.push({
        id: milestone.id,
        kind: 'milestone',
        label: milestone.name,
        meta: '',
        top,
        height: 46,
        milestone,
        startX,
        endX,
        width: point ? 14 : Math.max(18, endX - startX),
        point,
        inTrace: traceIds ? traceIds.has(milestone.id) : null,
      });
      top += 46;
    }
    this.rows = rows;
    this.bodyHeight = top;
    this.links = this.buildLinks(candidateLinks, traceIds);
    const today = this.dateMs(new Date().toISOString().slice(0, 10));
    this.todayX = today >= this.rangeStart && today <= this.rangeEnd ? this.x(today) : null;
  }

  private headingRow(id: string, kind: TimelineRowKind, label: string, meta: string, top: number, height: number): TimelineRow {
    return { id, kind, label, meta, top, height, milestone: null, startX: 0, endX: 0, width: 0, point: false, inTrace: null };
  }

  private calculateWidth(spanDays: number): number {
    if (this.fitToContainer && this.scroller) {
      return Math.max(680, this.scroller.nativeElement.clientWidth - LABEL_WIDTH);
    }
    const pixelsPerDay: Record<RoadmapZoom, number> = { year: .5, quarter: 1.15, month: 2.8, week: 8 };
    return Math.min(9000, Math.max(820, Math.round(spanDays * pixelsPerDay[this.zoom])));
  }

  private buildTicks(): TimelineTick[] {
    const ticks: TimelineTick[] = [];
    const date = new Date(this.rangeStart);
    if (this.zoom === 'year' || this.zoom === 'quarter') {
      date.setUTCDate(1);
      date.setUTCMonth(this.zoom === 'year' ? Math.floor(date.getUTCMonth() / 3) * 3 : date.getUTCMonth());
      while (date.getTime() <= this.rangeEnd) {
        const month = date.getUTCMonth();
        ticks.push({
          id: date.toISOString(),
          label: this.zoom === 'year' ? `Q${Math.floor(month / 3) + 1} ${date.getUTCFullYear()}` : date.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }),
          left: this.x(date.getTime()),
        });
        date.setUTCMonth(month + (this.zoom === 'year' ? 3 : 1));
      }
    } else {
      if (this.zoom === 'month') {
        const day = date.getUTCDay();
        date.setUTCDate(date.getUTCDate() - ((day + 6) % 7));
      }
      while (date.getTime() <= this.rangeEnd) {
        ticks.push({
          id: date.toISOString(),
          label: date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' }),
          left: this.x(date.getTime()),
        });
        date.setUTCDate(date.getUTCDate() + (this.zoom === 'month' ? 7 : 1));
      }
    }
    return ticks;
  }

  private buildLinks(candidates: RoadmapDependency[], traceIds: Set<string> | null): TimelineLink[] {
    const rows = new Map(this.rows.filter(row => row.milestone).map(row => [row.id, row]));
    return this.filterLinks(candidates, traceIds).flatMap(link => {
      const source = rows.get(link.source);
      const target = rows.get(link.target);
      if (!source || !target) return [];
      const sourceX = link.dependency_type === 'start_to_start' || link.dependency_type === 'start_to_finish' ? source.startX : source.endX;
      const targetX = link.dependency_type === 'finish_to_finish' || link.dependency_type === 'start_to_finish' ? target.endX : target.startX;
      const sourceY = source.top + source.height / 2;
      const targetY = target.top + target.height / 2;
      const bend = Math.max(24, Math.abs(targetX - sourceX) * .35);
      const direction = targetX >= sourceX ? 1 : -1;
      return [{
        id: link.id,
        path: `M ${sourceX} ${sourceY} C ${sourceX + bend * direction} ${sourceY}, ${targetX - bend * direction} ${targetY}, ${targetX} ${targetY}`,
        status: link.status,
        marker: this.marker(link.status),
      }];
    });
  }

  private filterLinks(links: RoadmapDependency[], traceIds: Set<string> | null): RoadmapDependency[] {
    if (this.linkMode === 'hidden') return [];
    if (this.linkMode === 'blocking') return links.filter(link => link.status === 'blocking' || link.status === 'at_risk');
    if (this.linkMode === 'trace') {
      if (!this.selectedMilestoneId || !traceIds) return [];
      return links.filter(link => traceIds.has(link.source) && traceIds.has(link.target));
    }
    return links;
  }

  private traceIds(links: RoadmapDependency[]): Set<string> | null {
    if (this.linkMode !== 'trace' || !this.selectedMilestoneId) return null;
    const traced = new Set<string>([this.selectedMilestoneId]);
    const queue = [this.selectedMilestoneId];
    while (queue.length) {
      const current = queue.shift() as string;
      links.forEach(link => {
        const neighbor = link.source === current ? link.target : link.target === current ? link.source : null;
        if (neighbor && !traced.has(neighbor)) {
          traced.add(neighbor);
          queue.push(neighbor);
        }
      });
    }
    return traced;
  }

  private marker(status: RoadmapDependency['status']): string {
    if (status === 'blocking') return 'url(#roadmap-arrow-blocking)';
    if (status === 'at_risk') return 'url(#roadmap-arrow-risk)';
    if (status === 'resolved') return 'url(#roadmap-arrow-resolved)';
    return 'url(#roadmap-arrow-default)';
  }

  private x(value: number): number {
    return Math.max(0, Math.min(this.timelineWidth, ((value - this.rangeStart) / (this.rangeEnd - this.rangeStart)) * this.timelineWidth));
  }

  private dateMs(value: string): number { return Date.parse(`${value}T00:00:00Z`); }

  private shortDate(value: string): string {
    if (!value) return 'Date not set';
    return new Date(this.dateMs(value)).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' });
  }
}
